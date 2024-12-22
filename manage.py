# read server.csv
import requests
import csv
import os
import argparse
import time


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
                raise ValueError(f"Download incomplete: {
                                 downloaded}/{total_size} bytes")

            os.makedirs(dir, exist_ok=True)
            path = os.path.join(dir, filename)

            with open(path, 'wb') as file:
                file.write(content)

            return True

        except (requests.RequestException, ValueError, IOError) as e:
            if attempt == max_retries - 1:
                print(f"\nError downloading {filename}: {str(e)}")
                return False
            print(f"\nRetrying download... (attempt {
                  attempt + 2}/{max_retries})")
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
    print('Done!')


def download_client_files():
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
    args = parser.parse_args()

    if args.client:
        start = time.time()
        clear_dir('mods/')
        download_common_files()
        download_client_files()
        print(f'Done! {(time.time() - start):.1f}s')
    elif args.server:
        start = time.time()
        clear_dir('mods/')
        clear_dir('plugins/')
        download_common_files()
        download_server_files()
        download_plugins_files()
        print(f'Done! {(time.time() - start):.1f}s')
    else:
        print('Please specify --client or --server')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
    except KeyboardInterrupt:
        print('Interrupted!')
