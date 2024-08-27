import os

import dearpygui.dearpygui as dpg

from multiprocessing import Pool
from pathlib import Path
from typing import Self

from Juneau.formats.bndl.bndl import BNDL
from Juneau.format_parsing.parser.bndl_parser import lazy_parse_bndl
import Juneau.config as consts

class BNDLTree():
    class Node():
        """Node of BNDL tree, data will be None if node is a directory
        """
        def __init__(self, data : BNDL) -> None:
            self.data : BNDL = data
            self.directories : dict[str, Self] = {}
            self.children : list[Self] = []

        def add_child(self, data : Self):
            self.children.append(data)

        def add_directory(self, dir_name : str, dir_node : Self):
            self.directories[dir_name] = dir_node

        def get_directory(self, dir_name : str) -> Self:
            return self.directories[dir_name]
        
        def has_directory(self, dir_name : str):
            return dir_name in self.directories
        

    def __init__(self, game_dir : str, bndl_list : list[BNDL]) -> None:
        self.__game_dir_path_length = len(Path(game_dir).parts)

        self.root = self.Node(None)

        for bndl in bndl_list:
            self.__add_bndl(bndl)

    def __add_bndl(self, bndl : BNDL):
        bndl_path = Path(bndl.full_file_path)

        current_node = self.root

        for parent_dir_part in bndl_path.parent.parts[self.__game_dir_path_length:]:
            if not current_node.has_directory(parent_dir_part):
                current_node.add_directory(parent_dir_part, self.Node(None))

            current_node = current_node.get_directory(parent_dir_part)

        current_node.add_child(self.Node(bndl))

    def get_bndls(self) -> list[BNDL]:
        return self.__get_bndls(self.root)

    def __get_bndls(self, bndl_node) -> list[BNDL]:
        bndl_list = []

        if bndl_node.data == None:             
            for directory in bndl_node.directories:
                bndl_list.extend( self.__get_bndls(bndl_node.directories[directory]) )
        # node is a bndl
        for child_bndl_node in bndl_node.children:
            bndl_list.append(child_bndl_node.data)

        return bndl_list

def __load_game_dir(game_dir, refresh_file_cache, progress_bar_tag) -> list[str]:
    print("Info: Loading BNDL filenames")

    file_list = []

    if not os.path.exists(consts.CACHE_DIRECTORY):
        os.makedirs(consts.CACHE_DIRECTORY)

    bndl_name_cache_filename = os.path.join(consts.CACHE_DIRECTORY, consts.BNDL_NAMES_CACHE_FILENAME)

    if os.path.isfile(bndl_name_cache_filename) and not refresh_file_cache:
        print("Info: Loading from cache")

        with open(bndl_name_cache_filename, "r") as f:
            for line in f:
                file_list.append(line.strip())

        return file_list
        
    print("Info: Overriding BNDL filename cache")

    counter = 1
    file_amt = sum([len(files) for r, d, files in os.walk(game_dir)]) # this is a little silly

    for subdir, _dirs, files in os.walk(game_dir):
        for file in files:
            full_file_name = os.path.join(subdir, file)

            dpg.set_value(progress_bar_tag, counter / file_amt)
            loading_text = dpg.get_item_user_data(progress_bar_tag)[0]
            dpg.set_value(loading_text, f"Scanning directory (This may take a while)\n{file} - ({counter}/{file_amt})")

            with open(full_file_name, "rb") as f:
                header = None
                try:
                    header = f.read(4).decode("utf-8")
                except UnicodeDecodeError:
                    continue

                if header == "bnd2":
                    file_list.append(full_file_name)

            counter += 1

    with open(bndl_name_cache_filename, "w") as f:
        for filename in file_list:
            f.write(filename + "\n")

    print("Info: Created new cache file and finished loading BNDL filenames")

    return file_list

# silly ah solution from https://stackoverflow.com/questions/4827432/how-to-let-pool-map-take-a-lambda-function
# needed because Pool.map has a hard time with lambda functions
class __LazyLoadBNDL(object):
    def __init__(self, is_hpr, BIG_ENDIAN):
        self.is_hpr = is_hpr
        self.BIG_ENDIAN = BIG_ENDIAN

    def __call__(self, res):
        return lazy_parse_bndl(res, self.is_hpr, self.BIG_ENDIAN)

def __lazy_load_all_bndls(bndl_filenames, is_hpr, big_endian, progress_bar_tag) -> list[BNDL]:
    print("Info: Lazy parsing BNDLs")

    bndl_list = []

    counter = 1
    bndl_amt = len(bndl_filenames)
    loading_text = dpg.get_item_user_data(progress_bar_tag)[0]

    for bndl_filename in bndl_filenames:
        dpg.set_value(progress_bar_tag, counter / bndl_amt)
        dpg.set_value(loading_text, f"{bndl_filename} - ({counter}/{bndl_amt})")
        
        bndl_list.append(__LazyLoadBNDL(is_hpr, big_endian)(bndl_filename))

        counter += 1

    print("Info: Finished lazy parsing BNDLs")

    return bndl_list

def get_bndl_tree(game_dir : str, is_hpr, big_endian, refresh_file_cache, progress_bar_tag) -> BNDLTree:
    return BNDLTree(game_dir, __lazy_load_all_bndls( __load_game_dir(game_dir, refresh_file_cache, progress_bar_tag), is_hpr, big_endian, progress_bar_tag ))