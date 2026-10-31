"""Supervised Elements Labs Telegram instance. No paid services.
Keeps server, quick tunnel and bot alive; updates Telegram after recovery.
The Mac must be running and online. No 24/7 hosting claim.
"""
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / 'runtime'
PORT = int(os.environ.get('ELEMENTS_PORT', '8766'))
ALLOWED_BOTS = {'elementslabs_shop_bot', 'elementslabsshop_bot', 'elementslabstest_bot'}  # Live-Bot des Inhabers und gemeinsamer Test-Bot
STOP = threading.Event()


class TelegramAuthError(RuntimeError):
    pass


def api(token, method, payload):
    request = urllib.request.Request('https://api.telegram.org/bot' + token + '/' + method,
                                     data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise TelegramAuthError('Telegram access refused; no automatic authentication retries') from None
        raise RuntimeError('Telegram API HTTP ' + str(error.code)) from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError('Telegram API temporarily unavailable') from None
    if not result.get('ok'):
        raise RuntimeError('Telegram API rejected ' + method)
    return result['result']


def tunnel_url(line):
    for value in re.findall(r'https://[a-z0-9-]+\.trycloudflare\.com\b', line):
        if value != 'https://api.trycloudflare.com':
            return value
    return ''


def healthy(origin):
    try:
        request = urllib.request.Request(origin.rstrip('/') + '/health', headers={'User-Agent': 'ElementsLive/1.0'})  # Cloudflare sperrt Python-urllib (Fehler 1010)
        with urllib.request.urlopen(request, timeout=10) as response:
            value = json.load(response)
        return value.get('status') == 'ok' and value.get('mode') == 'telegram' and value.get('products', 0) >= 25
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False


# A new quick-tunnel address is worse for customers than a short slow patch: restart only after two minutes of failures.
UNHEALTHY_LIMIT = 6


def restart_reason(processes, origin, probe=healthy, failures=0):
    for name, process in processes.items():
        if process.poll() is not None:
            return name + ' exited', failures
    failures = 0 if probe(origin) else failures + 1
    return ('public endpoint unhealthy' if failures >= UNHEALTHY_LIMIT else ''), failures


def atomic_text(path, text):
    temporary = path.with_suffix(path.suffix + '.next')
    temporary.write_text(text)
    os.replace(temporary, path)


def state(**values):
    values['updated_at'] = time.time()
    atomic_text(RUNTIME / 'status.json', json.dumps(values, ensure_ascii=False, indent=2) + '\n')


KEEP_AWAKE = ['/usr/bin/caffeinate', '-s', '-i', '-m']  # -s: kein Systemschlaf am Netzteil (auch bei geschlossenem Deckel), -i/-m: kein Leerlauf-/Plattenschlaf


def keep_awake():
    """Haelt den Mac wach, solange der Supervisor laeuft. Am Akku schlaeft ein MacBook bei geschlossenem Deckel trotzdem (macOS-Regel)."""
    try:
        return subprocess.Popen(KEEP_AWAKE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return None


def power_source():
    try:
        out = subprocess.run(['/usr/bin/pmset', '-g', 'batt'], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return 'unknown'
    return 'ac' if 'AC Power' in out else 'battery' if 'Battery Power' in out else 'unknown'


def stop_stack(processes):
    for process in reversed(list(processes.values())):
        if process.poll() is None:
            process.terminate()
    for process in processes.values():
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


FRONT_DIR = ROOT.parent / 'front'
FRONT = {'url': ''}


def front_url():
    try:
        return json.loads((FRONT_DIR / 'front.json').read_text()).get('url', '').rstrip('/')
    except (OSError, ValueError):
        return ''


def publish_front(tunnel):
    """Stabile Eingangstuer (Worker/Domain) auf den aktuellen Tunnel zeigen lassen. Faellt bei Fehler auf den Tunnel zurueck."""
    front = front_url()
    FRONT['url'] = ''
    if not front or not (FRONT_DIR / 'wrangler.toml').exists():
        return tunnel
    try:
        env = dict(os.environ)
        env['PATH'] = '/Users/eduardwart/.hermes/node/bin:' + env.get('PATH', '')
        result = subprocess.run(['npx', '-y', 'wrangler@latest', 'deploy', '--var', 'ORIGIN:' + tunnel],
                                cwd=FRONT_DIR, env=env, capture_output=True, text=True, timeout=150)
        if result.returncode != 0:
            print('FRONT: Veroeffentlichung fehlgeschlagen, direkter Tunnel bleibt aktiv', flush=True)
            return tunnel
        for _attempt in range(15):
            if healthy(front):
                FRONT['url'] = front
                return front
            time.sleep(2)
        print('FRONT: Eingangstuer antwortet nicht, direkter Tunnel bleibt aktiv', flush=True)
    except (OSError, subprocess.SubprocessError):
        print('FRONT: Fehler, direkter Tunnel bleibt aktiv', flush=True)
    return tunnel


def start_stack(env, token, bot_name):
    processes = {}
    try:
        log_path = RUNTIME / 'tunnel.log'
        with log_path.open('a') as log:
            offset = log.tell()
            processes['tunnel'] = subprocess.Popen(
                ['cloudflared', 'tunnel', '--no-autoupdate', '--url', f'http://127.0.0.1:{PORT}'],
                stderr=log, stdout=subprocess.DEVNULL)
        url = ''
        deadline = time.monotonic() + 75
        with log_path.open() as reader:
            reader.seek(offset)
            while time.monotonic() < deadline and not STOP.is_set():
                line = reader.readline()
                if line:
                    url = tunnel_url(line)
                    if url:
                        break
                elif processes['tunnel'].poll() is not None:
                    raise RuntimeError('Tunnel process exited during startup')
                else:
                    STOP.wait(.3)
        if not url:
            raise RuntimeError('No tunnel address received')
        processes['server'] = subprocess.Popen(
            [sys.executable, '-u', str(ROOT / 'server.py'), '--port', str(PORT), '--mode', 'telegram', '--public-origin', url], env=env)
        deadline = time.monotonic() + 75
        while time.monotonic() < deadline and not STOP.is_set():
            if processes['server'].poll() is not None:
                raise RuntimeError('Shop server exited during startup')
            if healthy(f'http://127.0.0.1:{PORT}') and healthy(url):
                break
            STOP.wait(2)
        else:
            raise RuntimeError('Shop did not become reachable')
        if STOP.is_set():
            raise RuntimeError('Startup cancelled')
        public = publish_front(url)
        atomic_text(RUNTIME / 'tunnel_origin.txt', url + '\n')
        atomic_text(RUNTIME / 'origin.txt', public + '\n')
        api(token, 'setChatMenuButton', {'menu_button': {'type': 'web_app', 'text': '🛒 Shop öffnen', 'web_app': {'url': public + '/'}}})
        for _attempt in range(8):  # Telegram uebernimmt den Menuknopf nicht immer sofort
            menu = api(token, 'getChatMenuButton', {})
            if menu.get('web_app', {}).get('url') == public + '/':
                break
            STOP.wait(2)
        else:
            raise RuntimeError('Telegram menu readback mismatch')
        processes['bot'] = subprocess.Popen([sys.executable, '-u', str(ROOT / 'bot.py')], env=env)
        return processes, url
    except Exception:
        stop_stack(processes)
        raise


def main():
    RUNTIME.mkdir(exist_ok=True)
    os.umask(0o077)
    lock = (RUNTIME / 'live.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('Elements Labs is already supervised.', flush=True)
        return
    env = dict(os.environ)
    for line in (RUNTIME / '.env.elements').read_text().splitlines():
        key, _, value = line.partition('=')
        if key and value:
            env[key] = value
    token = env['ELEMENTS_TELEGRAM_BOT_TOKEN']
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda _signal, _frame: STOP.set())
    while not STOP.is_set():
        try:
            identity = api(token, 'getMe', {})
            break
        except TelegramAuthError:
            raise
        except RuntimeError:
            state(status='recovering', reason='Telegram network unavailable at startup')
            STOP.wait(20)
    else:
        return
    bot_name = identity['username']
    if bot_name.lower() not in ALLOWED_BOTS:
        raise TelegramAuthError('Configured token belongs to a different bot; stopped')
    env['ELEMENTS_BOT_USERNAME'] = bot_name
    awake = keep_awake()
    subprocess.run([sys.executable, str(ROOT / 'build.py')], cwd=ROOT, check=True, env=env)
    restarts = 0
    try:
        while not STOP.is_set():
            processes = {}
            try:
                state(status='starting', restarts=restarts, bot=bot_name)
                processes, url = start_stack(env, token, bot_name)
                state(status='healthy', origin=FRONT['url'] or url, tunnel=url, bot=bot_name, restarts=restarts, power=power_source(),
                      pids={name: process.pid for name, process in processes.items()})
                print('LIVE:', FRONT['url'] or url, '| Tunnel:', url, '| Bot @' + bot_name, flush=True)
                failures = 0
                while not STOP.wait(20):
                    reason, failures = restart_reason(processes, url, failures=failures)
                    if reason:
                        if processes.get('bot') and processes['bot'].poll() == 2:
                            raise TelegramAuthError('Bot access refused')
                        state(status='recovering', origin=url, reason=reason, restarts=restarts)
                        print('RECOVERY:', reason, flush=True)
                        break
                    state(status='healthy' if not failures else 'checking', origin=FRONT['url'] or url, tunnel=url, bot=bot_name,
                          restarts=restarts, consecutive_failures=failures, power=power_source(),
                          pids={name: process.pid for name, process in processes.items()})
            except TelegramAuthError:
                state(status='blocked', reason='Telegram authentication refused', restarts=restarts)
                raise
            except (RuntimeError, OSError, ValueError):
                state(status='recovering', reason='Stack startup or network failure', restarts=restarts)
                print('RECOVERY: startup/network failure; retrying without exposing credentials', flush=True)
            finally:
                stop_stack(processes)
            if not STOP.is_set():
                restarts += 1
                STOP.wait(min(5 * restarts, 30))
    finally:
        if awake and awake.poll() is None:
            awake.terminate()
        state(status='stopped', bot=bot_name, restarts=restarts)
        lock.close()


if __name__ == '__main__':
    try:
        main()
    except TelegramAuthError:
        state(status='blocked', reason='Telegram access refused; no authentication retry')
        print('BLOCKED: Telegram access needs attention. Credentials were not changed.', flush=True)
        sys.exit(2)
