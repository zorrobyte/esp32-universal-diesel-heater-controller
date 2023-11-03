from ampy.pyboard import Pyboard
from ampy.files import Files

# Replace 'COM5' with the appropriate port on your system
port = 'COM5'


def get_file(filename):
    try:
        pyb = Pyboard(port)
        files = Files(pyb)
        contents = files.get(filename)
        with open(filename, 'wb') as file:
            file.write(contents)
        print(f"File {filename} has been successfully downloaded.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        pyb.close()


# Call the function with the name of the file you want to retrieve
get_file('config.json')
