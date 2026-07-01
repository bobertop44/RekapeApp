import os
from pathlib import Path



class FileChecking():
    dirs = False
    def Base():
        folder_path = os.path.join(os.path.expanduser("~"), "Documents", "Rekape","RekapeApp")
        if not os.path.exists(folder_path):
            dirs = False
            return False
        else:
            dirs = True
            return True
            
        

        