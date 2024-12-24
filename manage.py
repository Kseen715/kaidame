# read server.csv
import requests
import csv
import os
import argparse
import time
import base64

import ksilorama as ks
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

CLEAR = ks.Style.RESET_ALL
GREEN = ks.Fore.GREEN
RED = ks.Fore.RED


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


def get_file(frame: dict, dir: str, max_retries=5):
    url = frame['url']
    filename = frame['filename']
    download_file(url, dir, filename, max_retries)


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
    Decrypt the file using AES
    """
    with open(in_path, 'rb') as file:
        ct_bytes = file.read()

    cipher = AES.new(key, AES.MODE_CBC)
    ct_bytes = base64.b64decode(ct_bytes)
    pt = unpad(cipher.decrypt(ct_bytes), AES.block_size)

    with open(out_path, 'wb') as file:
        file.write(pt)


def generate_key():
    return get_random_bytes(32)


def read_key():
    with open('key', 'r') as file:
        key = file.read()
    return base64.b64decode(key)


def save_key(key):
    key = base64.b64encode(key).decode('utf-8')
    with open('key', 'w') as file:
        file.write(key)


def download_file(url, dir, filename, max_retries=3):
    def show_progress(downloaded, total, annotation='KB'):
        max_width = 40
        done = int(max_width * downloaded / total)
        print(f'\r[{"="*done}{" "*(max_width-done)
                              }] {downloaded:.1f}/{total:.1f} {annotation}', end='')

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
                show_progress(downloaded/1024, total_size/1024, "KB")

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
            print(f"\n{RED}Retrying download... (attempt {
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
    for file in files:
        # check if file is a jar file
        if file.endswith('.jar.enc'):
            # decrypt the file
            print(f"Decrypting {file}...")
            decrypt_file(read_key(), f'./getters/client/{file}', f'./mods/{file[:-4]}')

def download_client_files():
    install_crypto_client_files()
    data = read_csv('getters/client.csv')
    for frame in data:
        print(f"Downloading {frame['filename']}...")
        get_file(frame, 'mods/')



def download_server_files():
    data = read_csv('getters/server.csv')
    for frame in data:
        print(f"Downloading {frame['filename']}...")
        get_file(frame, 'mods/')


def download_plugins_files():
    data = read_csv('getters/plugins.csv')
    for frame in data:
        print(f"Downloading {frame['filename']}...")
        get_file(frame, 'plugins/')


def download_common_files():
    data = read_csv('getters/common.csv')
    for frame in data:
        print(f"Downloading {frame['filename']}...")
        get_file(frame, 'mods/')


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
        download_common_files()
        download_client_files()
        print(f'{GREEN}Done! {(time.time() - start):.1f}s{CLEAR} ')
    elif args.server:
        start = time.time()
        clear_dir('mods/')
        clear_dir('plugins/')
        download_common_files()
        download_server_files()
        download_plugins_files()
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
