<?php
declare(strict_types=1);

/* Minimal HEX key API. No admin key and no extra authentication. */
const STORE = __DIR__ . '/keys.json';
const PREFIX = 'HEX-CHATS-';

header('Cache-Control: no-store');
header('Content-Type: application/json; charset=utf-8');

define('NOW_UTC', new DateTimeZone('UTC'));

function respond(array $data, int $status = 200): never {
    http_response_code($status);
    echo json_encode($data, JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);
    exit;
}

function input(): array {
    $json = json_decode(file_get_contents('php://input') ?: '', true);
    if (is_array($json)) return $json;
    return $_POST ?: $_GET;
}

function load_keys(): array {
    if (!is_file(STORE)) return [];
    $data = json_decode((string) file_get_contents(STORE), true);
    return is_array($data) ? $data : [];
}

function save_keys(array $keys): void {
    $tmp = STORE . '.tmp';
    file_put_contents($tmp, json_encode($keys, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES), LOCK_EX);
    rename($tmp, STORE);
}

function number_value(array $body, string $name, int $default): int {
    $value = $body[$name] ?? $default;
    return is_numeric($value) ? (int) $value : $default;
}

function validity_label(int $days, int $hours): string {
    $parts = [];
    if ($days > 0) $parts[] = $days . ' Day' . ($days === 1 ? '' : 's');
    if ($hours > 0) $parts[] = $hours . ' Hour' . ($hours === 1 ? '' : 's');
    return $parts ? implode(' ', $parts) : '0 Hours';
}

function key_response(string $key, array $record): array {
    return [
        'ok' => true,
        'key' => $key,
        'validity' => $record['validity'],
        'expires_at' => $record['expires_at'],
        'max_devices' => $record['max_devices'],
        'hours' => $record['hours'],
    ];
}

function b64url(string $value): string {
    return rtrim(strtr(base64_encode($value), '+/', '-_'), '=');
}

function access_token(string $key, int $seconds): string {
    $header = b64url(json_encode(['alg' => 'none', 'typ' => 'JWT']));
    $payload = b64url(json_encode(['sub' => $key, 'tier' => 'standard', 'iat' => time(), 'exp' => time() + $seconds]));
    return $header . '.' . $payload . '.demo';
}

$body = input();
$action = strtolower((string) ($body['action'] ?? $_GET['action'] ?? $_GET['api'] ?? ''));

if ($action === 'challenge') {
    respond(['nonce' => bin2hex(random_bytes(32))]);
}

/* POST/GET ?action=create
 * Body/query: days, hours, max_devices
 * Example: ?action=create&hours=10&max_devices=1
 */
if ($action === 'create' || $action === 'generate' || $action === 'new') {
    $days = max(0, number_value($body, 'days', 0));
    $hoursOnly = max(0, number_value($body, 'hours', 10));
    $maxDevices = max(1, min(100, number_value($body, 'max_devices', 1)));
    $totalHours = ($days * 24) + $hoursOnly;
    if ($totalHours < 1) $totalHours = 1;

    $now = new DateTime('now', NOW_UTC);
    $expires = (clone $now)->modify('+' . $totalHours . ' hours');
    $key = PREFIX . strtoupper(bin2hex(random_bytes(4)));
    $record = [
        'created_at' => $now->format('Y-m-d H:i:s'),
        'expires_at' => $expires->format('Y-m-d H:i:s'),
        'hours' => $totalHours,
        'days' => $days,
        'validity' => validity_label($days, $hoursOnly),
        'max_devices' => $maxDevices,
        'devices' => [],
    ];
    $keys = load_keys();
    $keys[$key] = $record;
    save_keys($keys);
    respond(key_response($key, $record));
}

/* POST ?action=activate
 * Body: {"key":"HEX-CHATS-...","device_id":"phone-1"}
 * The APK can also send license_key and device_pubkey.
 */
if ($action === 'activate' || $action === 'validate') {
    $key = strtoupper(trim((string) ($body['key'] ?? $body['license_key'] ?? '')));
    $device = trim((string) ($body['device_id'] ?? $body['device_pubkey'] ?? ''));
    if ($device === '' && isset($body['fingerprint_inputs'])) {
        $device = is_string($body['fingerprint_inputs'])
            ? $body['fingerprint_inputs']
            : json_encode($body['fingerprint_inputs']);
    }
    if ($key === '' || $device === '') respond(['ok' => false, 'error' => 'key and device_id are required'], 400);

    $keys = load_keys();
    if (!isset($keys[$key])) respond(['ok' => false, 'error' => 'invalid key'], 401);
    $record = $keys[$key];
    $expires = strtotime((string) $record['expires_at'] . ' UTC');
    if ($expires === false || $expires <= time()) respond(['ok' => false, 'error' => 'key expired'], 401);

    $deviceHash = hash('sha256', $device);
    $devices = array_values(array_unique(array_map('strval', $record['devices'] ?? [])));
    if (!in_array($deviceHash, $devices, true) && count($devices) >= (int) $record['max_devices']) {
        respond(['ok' => false, 'error' => 'device limit reached', 'max_devices' => $record['max_devices']], 403);
    }
    if (!in_array($deviceHash, $devices, true)) {
        $devices[] = $deviceHash;
        $keys[$key]['devices'] = $devices;
        save_keys($keys);
    }
    $remaining = max(1, $expires - time());
    respond([
        'ok' => true,
        'key' => $key,
        'validity' => $record['validity'],
        'expires_at' => $record['expires_at'],
        'max_devices' => $record['max_devices'],
        'hours' => $record['hours'],
        'message' => 'activated',
        'access_token' => access_token($key, $remaining),
        'refresh_token' => access_token($key, $remaining),
        'lease' => $record['expires_at'],
        'tier' => 'standard',
        'config_version' => 1,
    ]);
}

respond([
    'ok' => true,
    'api' => 'HEX key generator',
    'usage' => [
        'create' => 'POST or GET ?action=create&days=0&hours=10&max_devices=1',
        'activate' => 'POST ?action=activate with key and device_id',
    ],
]);
