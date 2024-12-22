# read server.csv
import requests
import csv
import os
import argparse


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


def get_file(frame: dict, dir: str):
    """
    Get a file from url and save it to dir
    Use requests.get to get the file
    """
    response = requests.get(frame['url'])
    # if dir does not exist, create it
    if not os.path.exists(dir):
        os.makedirs(dir)
    path = dir + frame['filename']
    with open(path, 'wb') as file:
        file.write(response.content)


def clear_dir(dir: str):
    """
    Clear the directory
    """
    if not os.path.exists(dir):
        return
    print(f"Clearing {dir}... ", end='')
    for file in os.listdir(dir):
        os.remove(dir + file)
    print('Done!')


def download_client_files():
    data = read_csv('getters/client.csv')
    for frame in data:
        print(f"Downloading {frame['filename']}... ", end='')
        get_file(frame, 'mods/')
        print('Done!')


def download_server_files():
    data = read_csv('getters/server.csv')
    for frame in data:
        print(f"Downloading {frame['filename']}... ", end='')
        get_file(frame, 'mods/')
        print('Done!')


def download_common_files():
    data = read_csv('getters/common.csv')
    for frame in data:
        print(f"Downloading {frame['filename']}... ", end='')
        get_file(frame, 'mods/')
        print('Done!')


def main():
    parser = argparse.ArgumentParser(description='Download mods for client or server')
    parser.add_argument('--client', action='store_true', help='Download mods for client')
    parser.add_argument('--server', action='store_true', help='Download mods for server')
    args = parser.parse_args()

    if args.client:
        clear_dir('mods/')
        download_common_files()
        download_client_files()
    elif args.server:
        clear_dir('mods/')
        download_common_files()
        download_server_files()
    else:
        print('Please specify --client or --server')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(e)
    except KeyboardInterrupt:
        print('Interrupted!')