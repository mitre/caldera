import abc


class FileServiceInterface(abc.ABC):

    @abc.abstractmethod
    def get_file(self, headers):
        """
        Retrieve file
        :param headers: headers dictionary. The `file` key is REQUIRED.
        :type headers: dict or dict-equivalent
        :return: File contents and optionally a display_name if the payload is a special payload
        :raises: KeyError if file key is not provided, FileNotFoundError if file cannot be found
        """
        raise NotImplementedError

    @abc.abstractmethod
    def save_file(self, filename, payload, target_dir):
        raise NotImplementedError

    @abc.abstractmethod
    def create_exfil_sub_directory(self, dir_name):
        raise NotImplementedError

    @abc.abstractmethod
    def save_multipart_file_upload(self, request, target_dir):
        """
        Accept a multipart file via HTTP and save it to the server
        :param request:
        :param target_dir: The path of the directory to save the uploaded file to.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def find_file_path(self, name, location):
        """
        Find the location on disk of a file by name.
        :param name:
        :param location:
        :return: a tuple: the plugin the file is found in & the relative file path
        """
        raise NotImplementedError

    @abc.abstractmethod
    def read_file(self, name, location):
        """
        Open a file and read the contents
        :param name:
        :param location:
        :return: a tuple (file_path, contents)
        """
        raise NotImplementedError

    @abc.abstractmethod
    def read_result_file(self, link_id, location):
        """
        Read a result file. If file encryption is enabled, this method will return the plaintext
        content.  Returns contents as a base64 encoded dictionary.
        :param link_id: The id of the link to return results from.
        :param location: The path to results directory.
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def write_result_file(self, link_id, output, location):
        """
        Writes the results of a link execution to disk. If file encryption is enabled,
        the results file will contain ciphertext.
        :param link_id: The link id of the result being written.
        :param output: The content of the link's output.
        :param location: The path to the results directory.
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_special_payload(self, name, func):
        """
        Call a special function when specific payloads are downloaded
        :param name:
        :param func:
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def compile_go(self, platform, output, src_fle, arch, ldflags, cflags, buildmode, build_dir, loop):
        """
        Dynamically compile a go file
        :param platform:
        :param output:
        :param src_fle:
        :param arch: Compile architecture selection (defaults to AMD64)
        :param ldflags: A string of ldflags to use when building the go executable
        :param cflags: A string of CFLAGS to pass to the go compiler
        :param buildmode: GO compiler buildmode flag
        :param build_dir: The path to build should take place in
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_payload_name_from_uuid(self, payload):
        raise NotImplementedError
