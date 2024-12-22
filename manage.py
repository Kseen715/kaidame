# read server.csv
import requests
import csv
import os

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
    for file in os.listdir(dir):
        os.remove(dir + file)


def download_client_files():
    data = read_csv('getters/client.csv')
    for frame in data:
        get_file(frame, 'mods/')

def download_server_files():
    data = read_csv('getters/server.csv')
    for frame in data:
        get_file(frame, 'mods/')

def download_common_files():
    data = read_csv('getters/common.csv')
    for frame in data:
        get_file(frame, 'mods/')

if __name__ == "__main__":
    clear_dir('mods/')
    download_client_files()
    download_server_files()
    download_common_files()
