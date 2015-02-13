import os
import json
import logging

class DbEntry(object):
    def __init__(self, root, command, file_path):
        self.root = root
        self.command = command
        self.file_path = file_path
    
    def FileExists(self):
        return os.path.exists(self.file_path)

    def __repr__(self):
        return "DbEntry(command='%s', file_path='%s'" % (self.command, self.file_path)

class DbEntryEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, DbEntry):
            db_entry_dict = {
                "directory": obj.root,
                "command": obj.command,
                "file": obj.file_path
            }
            return db_entry_dict
        return json.JSONEncoder.default(self, obj)

def DbEntryDecoder(dct):
    if "file" in dct:
        return DbEntry(dct["directory"], dct["command"], dct["file"])
    return dct

class Database(object):
    def __init__(self, configuration):
        self._root = configuration.GetExpandedDir("projects","root_dir")
        self._compile_commands_file_path = os.path.join(
                self._root, "compile_commands.json")
        self._database = {}
        self._LoadDatabase()

    def _LoadDatabase(self):
        if os.path.exists(self._compile_commands_file_path):
            try:
                with open(self._compile_commands_file_path, "r") as f:
                    database_list = json.load(f, object_hook=DbEntryDecoder)
                    self._database = {}
                    for db_list_entry in database_list:
                        self._database[db_list_entry.file_path] = db_list_entry
                    self._CleanFromNonExisting()
                logging.info("Loaded previous compilation database: %d entries",
                        len(self._database))
            except ValueError as e:
                logging.warning("Compilation database is corrupted, "
                                "making empty database...")

    def _CleanFromNonExisting(self):
        new_database = {}
        for _, entry in self._database.items():
            if entry.FileExists():
                new_database[entry.file_path] = entry
        self._database = new_database

    def SubmitCommand(self, file_name, command):
        self._database[file_name] = DbEntry(self._root, command, file_name)

    def Write(self):
        self._CleanFromNonExisting()
        with open(self._compile_commands_file_path, "w") as f:
            db_list = []
            for _, value in self._database.items():
                db_list.append(value)
            json.dump(db_list,fp=f, cls=DbEntryEncoder)
