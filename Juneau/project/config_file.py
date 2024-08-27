import os
import json

class ConfigFile():
    def __init__(self, config_path, config_filename) -> None:
        self.__config_path : str = config_path
        self.__config_filename : str = config_filename

        self.__config : dict = self.__load_config()

    def get_config_option(self, option : str) -> any:
        """Returns a given config option

        Args:
            option (str): The option to get, see Juneau.proj.config for config options

        Raises:
            ConfigOptionNotFoundException: Exception raised if option is not found

        Returns:
            any: The value of the config option, can be any type able to be stored in json
        """
        if option in self.__config:
            return self.__config[option]
        else:
            raise ConfigOptionNotFoundException(f"Config option not found: {option}")
        
    def set_config_option(self, option : str, value : any, save = True):
        """Sets a configuration option 

        Args:
            option (str): The option to set, see Juneau.proj.config for config options
            value (any): The new value for config option, can be any type able to be stored in json
            save (bool, optional): Determines whether to save the file after setting the option. Defaults to True.
        """
        if option in self.__config:
            if not isinstance(value, type(self.__config[option])):
                print(f"Warning: Type mismatch when setting config option: {option}; Type {type(value)} ({value}) != Type{type(self.__config[option])} ({self.__config[option]})")
        else:
            print(f"Info: Creating new config option: {option}")

        self.__config[option] = value

        if save:
            self.save_config()

    def has_config_option(self, option : str) -> bool:
        """Returns whether or not the config file has a given option.

        Args:
            option (str): The config option to check.

        Returns:
            bool: True if the config option exists, false otherwise.
        """
        return option in self.__config

    def save_config(self) -> None:
        """Saves the configuration file to disk
        """
        with open(self.__get_full_config_path(), "w") as f:
            json.dump(self.__config, f)

    def __load_config(self) -> dict:
        if os.path.isfile(self.__get_full_config_path()):
            with open(self.__get_full_config_path(), "r") as f:
                return json.load(f)
        else:
            print("Warning: Returning blank config dict as no config file was found")

        return {}

    def __get_full_config_path(self) -> str:
        return f"{self.__config_path}/{self.__config_filename}"

class ConfigOptionNotFoundException(Exception):
    """Exception raised when trying to retrieve an option that isnt present in the 
        configuration file
    """
