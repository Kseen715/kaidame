# read server.csv
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import requests
import csv
import os
import argparse
import time
import base64
import threading

import ksilorama as ks
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

MODRINTH_BASE_URL = "https://cdn.modrinth.com"
MODRINTH_API = "https://api.modrinth.com/v2"
CURSEFORGE_BASE_URL = "https://www.curseforge.com"
CURSEFORGE_API = "https://api.curseforge.com/v1"
CURSEFORGE_API_OLD = "https://www.curseforge.com/api/v1"
CURSEFORGE_API_KEY = "https://cf.polymc.org/api"  # Thanks to PolyMC

USE_THREADING = True
THREADS = 32
THREADS = max(THREADS, os.cpu_count())

# Colors
CLEAR = ks.Style.RESET_ALL
GREEN = ks.Fore.GREEN
YELLOW = ks.Fore.YELLOW
RED = ks.Fore.RED
CYAN = ks.Fore.CYAN
UPDATING = CYAN
DECRYPTING = ks.Fore.MAGENTA


def read_csv(filename: str) -> list:
    with open(filename, 'r') as file:
        reader = csv.reader(file)
        data = list(reader)
    if len(data) == 0:
        return []
    header = data[0]
    data = data[1:]
    # construct a dictionary
    data = [{header[i]: data[j][i]
             for i in range(len(header))} for j in range(len(data))]
    return data


def get_file(
    frame: dict, dir: str, max_retries=5,
    mc_version: str = "1.20.1",
    modloader: str = "forge",
    quiet=False
):
    url = frame['url']
    filename = frame['filename']
    # if url in in pattern "https://cdn.modrinth.com/data/XXXXXXXX/"
    if url.startswith(MODRINTH_BASE_URL + '/data/'):
        # Modrinth
        if 'versions/' in url:
            download_file(url, dir, filename, max_retries, quiet)
            return
        else:
            if not quiet:
                print(f'{UPDATING}', end='')
            # get version
            project_id = list(filter(None, url.split('/')))[-1]
            all_version = requests.get(
                f"{MODRINTH_API}/project/{project_id}/version"
            ).json()
            # if mc_version is not in game_versions, remove it from the list
            filtered_version = list(filter(
                lambda x: mc_version in x['game_versions'], all_version)
            )
            # if modloader is not in loaders, remove it from the list
            filtered_version = list(filter(
                lambda x: modloader in x['loaders'], filtered_version)
            )
            # sort by date_published
            filtered_version = sorted(
                filtered_version, key=lambda x: x['date_published'], reverse=True
            )
            latest = filtered_version[0]
            url = latest['files'][0]['url']
            new_filename = latest['files'][0]['filename']
            download_file(url, dir, new_filename, max_retries, quiet)
            if not quiet:
                print(f'{CLEAR}', end='')
            return
    elif url.startswith(CURSEFORGE_API) or url.startswith(CURSEFORGE_API_OLD):
        # CurseForge
        if 'files/' in url:
            download_file(url, dir, filename, max_retries, quiet)
            return
        else:
            if not quiet:
                print(f'{UPDATING}', end='')
            # get project_id
            project_id = list(filter(None, url.split('/')))[-1]
            # get all files
            api_key = requests.get(CURSEFORGE_API_KEY).json()['token']
            all_files = requests.get(
                f"{CURSEFORGE_API}/mods/{project_id}/files",
                params={
                    'gameVersion': mc_version,
                    'modLoaderType': modloader.capitalize(),
                },
                headers={'x-api-key': api_key}
            ).json()
            # in gameVersions check if mc_version is in it and modloader is in it
            all_files = all_files['data']
            all_files = list(filter(
                lambda x: mc_version in x['gameVersions'] and modloader.lower(
                ) in [v.lower() for v in x['gameVersions']],
                all_files
            )
            )
            # sort by dateModified
            all_files = sorted(
                all_files, key=lambda x: x['fileDate'], reverse=True
            )
            latest = all_files[0]
            vesrion_id = latest['id']
            new_filename = latest['fileName']
            url = latest['downloadUrl']
            # url = f"{CURSEFORGE_API}/mods/{project_id}/files/{vesrion_id}/download"
            download_file(url, dir, new_filename, max_retries, quiet)
            if not quiet:
                print(f'{CLEAR}', end='')
            return
    else:
        # direct download
        download_file(url, dir, filename, max_retries, quiet)


def show_progress(downloaded, total):
    """
    Show download progress

    Args:
        downloaded: downloaded size in bytes
        total: total size in bytes
    """
    max_width = 40
    if total >= 1024**3:
        total /= 1024**3
        downloaded /= 1024**3
        annotation = 'GB'
    elif total >= 1024**2:
        total /= 1024**2
        downloaded /= 1024**2
        annotation = 'MB'
    elif total >= 1024**1:
        total /= 1024
        downloaded /= 1024
        annotation = 'KB'
    else:
        annotation = 'B'
    done = int(max_width * downloaded / total)
    print(f'\r[{"="*done}{" "*(max_width-done)
                          }] {downloaded:.1f}/{total:.1f} {annotation}', end='')


def encrypt_file(key: str, in_path: str, out_path: str):
    """
    Encrypt the file using AES
    """
    with open(in_path, 'rb') as file:
        content = file.read()

    cipher = AES.new(key, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(content, AES.block_size))
    ct_bytes = base64.b64encode(ct_bytes).decode('utf-8')

    with open(out_path, 'wb') as file:
        file.write(ct_bytes.encode('utf-8'))


def decrypt_file(key: str, in_path: str, out_path: str):
    """
    Decrypt the file using AES streaming chunks
    """
    print(f'{DECRYPTING}', end='')
    CHUNK_SIZE = 4096  # 1MB chunks
    total_size = os.path.getsize(in_path)
    processed = 0

    cipher = AES.new(key, AES.MODE_CBC)

    with open(in_path, 'rb') as infile, open(out_path, 'wb') as outfile:
        while True:
            chunk = infile.read(CHUNK_SIZE)
            if not chunk:
                break

            processed += len(chunk)
            show_progress(processed, total_size)

            # Decode base64
            chunk = base64.b64decode(chunk)

            # For last chunk, handle padding
            if len(chunk) % AES.block_size != 0:
                chunk = pad(chunk, AES.block_size)

            # Decrypt and write
            pt = cipher.decrypt(chunk)

            # Remove padding from last chunk
            if processed >= total_size:
                pt = unpad(pt, AES.block_size)

            outfile.write(pt)
    print(f'{CLEAR}')


def generate_key():
    return get_random_bytes(32)


def read_key():
    try:
        with open('key', 'r') as file:
            key = file.read()
    except FileNotFoundError:
        raise FileNotFoundError('Key not found! Please create a ./key first.')
    return base64.b64decode(key)


def save_key(key):
    key = base64.b64encode(key).decode('utf-8')
    with open('key', 'w') as file:
        file.write(key)


def download_file(url, dir, filename, max_retries=3, quiet=False):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            if total_size == 0:
                raise ValueError("Content-Length header missing")

            downloaded = 0
            content = bytearray()

            for chunk in response.iter_content(chunk_size=8192):
                downloaded += len(chunk)
                content.extend(chunk)
                if not quiet:
                    show_progress(downloaded, total_size)

            if not quiet:
                print()  # New line after download

            if downloaded != total_size:
                raise ValueError(f"{RED}Download incomplete: {
                                 downloaded}/{total_size} bytes{CLEAR} ")

            os.makedirs(dir, exist_ok=True)
            path = os.path.join(dir, filename)

            with open(path, 'wb') as file:
                file.write(content)

            return True

        except (requests.RequestException, ValueError, IOError) as e:
            if attempt == max_retries - 1:
                print(f"\n{RED}Error downloading {filename}: {str(e)}{CLEAR} ")
                return False
            prefix = ''
            if USE_THREADING:
                prefix = '\n'
            print(f"{prefix}{YELLOW}Something went wrong. Retrying download... (attempt {
                  attempt + 2}/{max_retries}){CLEAR} ")
            time.sleep(1)


def clear_dir(dir: str, extensions=['.jar', '.zip']):
    """
    Clear the directory
    """
    if not os.path.exists(dir):
        return
    print(f"Clearing {dir}... ", end='')
    for file in os.listdir(dir):
        if any(file.endswith(ext) for ext in extensions):
            os.remove(dir + file)
    print(f'{GREEN}Done!{CLEAR} ')


def install_crypto_client_files():
    # install files from ./getters/client
    files = os.listdir('./getters/client')
    try:
        for file in files:
            # check if file is a jar file
            if file.endswith('.jar.enc'):
                # decrypt the file
                print(f"Decrypting {file}...")
                decrypt_file(
                    read_key(), f'./getters/client/{file}', f'./mods/{file[:-4]}')
    except Exception as e:
        print(f'{YELLOW}{e} Skipping encrypted stuff...{CLEAR} ')


def run_get_file_threaded(data: list, desc: str, dir: str):
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        # Create progress bar
        pbar = tqdm(
            total=len(data),
            desc=desc,
            unit="file",
            bar_format="{desc}: {percentage:3.0f}% [{bar}] {n_fmt:>3}/{total_fmt:>3} [{elapsed:>5}<{remaining:>5}]",
            ascii=" =",
        )
        # Submit all download tasks
        futures = [executor.submit(
            get_file, frame, dir, modloader=frame['loader'], quiet=True) for frame in data]
        # Update progress as downloads complete
        for _ in concurrent.futures.as_completed(futures):
            pbar.update(1)
        pbar.close()


def download_client_files():
    install_crypto_client_files()
    data = read_csv('getters/client.csv')
    if len(data) < 1:
        return
    if USE_THREADING:
        run_get_file_threaded(
            data,
            "[ 💫 ] Downloading client files",
            'mods/'
        )
    else:
        for frame in data:
            print(f"Downloading {frame['filename']}...")
            get_file(frame, 'mods/', modloader=frame['loader'])


def download_server_files():
    data = read_csv('getters/server.csv')
    if len(data) < 1:
        return
    if USE_THREADING:
        run_get_file_threaded(
            data,
            "[ 💭 ] Downloading server files",
            'mods/'
        )
    else:
        for frame in data:
            print(f"Downloading {frame['filename']}...")
            get_file(frame, 'mods/', modloader=frame['loader'])


def download_plugins_files():
    data = read_csv('getters/plugins.csv')
    if len(data) < 1:
        return
    if USE_THREADING:
        run_get_file_threaded(
            data,
            "[ 🧩 ] Downloading plugins     ",
            'plugins/'
        )
    else:
        for frame in data:
            print(f"Downloading {frame['filename']}...")
            get_file(frame, 'plugins/', modloader=frame['loader'])


def download_common_files():
    data = read_csv('getters/common.csv')
    if len(data) < 1:
        return
    if USE_THREADING:
        run_get_file_threaded(
            data,
            "[ 📦 ] Downloading common files",
            'mods/'
        )
    else:
        for frame in data:
            print(f"Downloading {frame['filename']}...")
            get_file(frame, 'mods/', modloader=frame['loader'])


def main():
    parser = argparse.ArgumentParser(
        description='Download mods for client or server')
    parser.add_argument('--client', action='store_true',
                        help='Download mods for client')
    parser.add_argument('--server', action='store_true',
                        help='Download mods for server')
    parser.add_argument('--key', action='store_true',
                        help='Generate key for encryption')
    parser.add_argument('--encrypt', type=str, help='Encrypt file')
    args = parser.parse_args()

    if args.client:
        start = time.time()
        clear_dir('mods/')
        clear_dir('plugins/')
        download_client_files()
        download_common_files()
        print(f'{GREEN}Done! {(time.time() - start):.1f}s{CLEAR} ')
    elif args.server:
        start = time.time()
        clear_dir('mods/')
        clear_dir('plugins/')
        download_server_files()
        download_plugins_files()
        download_common_files()
        print(f'{GREEN}Done! {(time.time() - start):.1f}s{CLEAR} ')
    elif args.key:
        save_key(generate_key())
        print(f'{GREEN}Key generated and saved! ./key{CLEAR} ')
        # print(read_key())
        # encrypt_file(key, 'mods/OptiFine_1.20.1_HD_U_I6.jar',
        #              'mods/optiflex.enc')
        # decrypt_file(key, 'mods/optiflex.enc', 'mods/optiflex.jar')
    elif args.encrypt:
        key = read_key()
        encrypt_file(key, args.encrypt, args.encrypt + '.enc')
    else:
        print('Please specify --client or --server')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
    except KeyboardInterrupt:
        print('Interrupted!')
