import argparse
import subprocess
import re
import os
import requests
import tarfile
from typing import Optional, List, Dict


NOT_FOUND_ERROR = "Arquivo ou pasta não encontrado."

class InstallAndConfigure:
    @staticmethod
    def download_file(url: str, dest_path: str) -> None:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(dest_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

    @staticmethod
    def extract_tar_gz(file_path: str, extract_path: str) -> None:
        with tarfile.open(file_path, 'r:gz') as tar:
            tar.extractall(path=extract_path)

    @staticmethod
    def move_executable(src_path: str, dest_path: str) -> None:
        if not os.path.exists(os.path.dirname(dest_path)):
            os.makedirs(os.path.dirname(dest_path))
        subprocess.run(['sudo', 'mv', src_path, dest_path], check=True)

    @staticmethod
    def create_alias() -> None:
        config_file = os.path.expanduser('~/.bashrc')
        alias_command = f"alias gd='python3 /home/louise/Documents/gd.py'\n"

        with open(config_file, 'a') as file:
            file.write(alias_command)

        subprocess.run('source ~/.bashrc', shell=True)

    @staticmethod
    def install_gdrive() -> None:
        InstallAndConfigure.create_alias()

        url = "https://github.com/glotlabs/gdrive/releases/download/3.9.1/gdrive_linux-x64.tar.gz"
        download_path = "/tmp/gdrive_linux-x64.tar.gz"
        extract_path = "/tmp/gdrive"
        dest_path = "/usr/local/bin/gdrive"

        InstallAndConfigure.download_file(url, download_path)
        InstallAndConfigure.extract_tar_gz(download_path, extract_path)
        InstallAndConfigure.move_executable(os.path.join(extract_path, "gdrive"), dest_path)

        os.chmod(dest_path, 0o755)


def to_dict(output: str) -> Dict[str, Optional[str]]:
    lines = output.splitlines()
    headers = [header.strip() for header in lines[0].split()]
    values = [value.strip() for value in lines[1].split(maxsplit=4)]

    data_dict = dict(zip(headers, values))
    data_dict['Type'] = data_dict['Type'] or None
    return data_dict

def format_output(output_text: str) -> str:

    headers = ['Nome', 'Tipo', 'Tamanho']
    type_translation = {
        'document': 'google doc',
        'regular': 'arquivo',
        'folder': 'pasta'
    }

    lines = output_text.strip().split('\n')
    processed_rows = []

    for line in lines[1:]:
        match = re.match(r'\s*[^\s]+\s+(.+?)\s+(folder|document|regular)\s+([\d\.]+\s\w+|)', line)
        if match:
            name = match.group(1).strip()
            file_type = type_translation.get(match.group(2).strip(), match.group(2))
            size = match.group(3).strip() if match.group(3) else ''
            processed_rows.append([name, file_type, size])

    print('')
    print(f"{headers[0]:<50} {headers[1]:<15} {headers[2]:<10}")
    print('-' * 75)

    for row in processed_rows:
        print(f"{row[0]:<50} {row[1]:<15} {row[2]:<10}")


class GDRiveCommand:
    def _execute(self, command: List[str]) -> Optional[str]:
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, text=True, check=True)
            if len(result.stdout.splitlines()) <= 1:
                return None
            return result.stdout
        except subprocess.CalledProcessError as e:
            logging.error(f"Command '{' '.join(command)}' failed with error: {e}")
            return None

    def _build_command(self, *args: str) -> List[str]:
        return ['gdrive', 'files', *args]

    def _get_object(self, object_name: str, parent_id: Optional[str] = None, return_only_id: bool = True) -> Optional[str]:
        query = f"name='{object_name}'"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        result = self._execute(self._build_command('list', '--query', query))
        if not result:
            raise ValueError(NOT_FOUND_ERROR)
        if return_only_id:
            return result.splitlines()[1].split()[0] if result else None
        return to_dict(result) if result else None

    def _get_nested_object(self, path: str) -> Optional[str]:
        try:
            path_components = path.split('/')
            file_name = path_components.pop()
            parent_id = None

            for folder_name in path_components:
                parent_id = self._get_object(object_name=folder_name, parent_id=parent_id)

            file_object = self._get_object(object_name=file_name, parent_id=parent_id, return_only_id=False)
            return file_object
        except ValueError as e:
            return str(e)

    def list_home(self) -> Optional[str]:
        output =  self._execute(self._build_command('list', '--order-by', 'modifiedTime desc'))
        return format_output(output) if output else " "

    def search_by_name(self, object_name: str) -> Optional[str]:
        output = self._execute(self._build_command('list', '--full-name', '--query', f"name contains '{object_name}'"))
        return format_output(output) if output else " "

    def list_folder(self, folder_path: Optional[str]) -> Optional[str]:
        folder_names = folder_path.split('/')
        parent_id = None
        try:
            for folder_name in folder_names:
                parent_id = self._get_object(folder_name, parent_id)
            output = self._execute(self._build_command('list', '--full-name', '--query', f"'{parent_id}' in parents", '--order-by', 'modifiedTime desc'))
            return format_output(output) if output else " "
        except ValueError as e:
            return str(e)

    def export_google_doc(self, object: Dict) -> Optional[str]:
        print("O arquivo selecionado é um documento do Google. Você pode exportá-lo para diferentes formatos.")
        print('')
        print("Escolha o formato de exportação:")
        print("1. PDF (Documento PDF)")
        print("2. DOCX (Documento do Word)")
        print("3. ODT (Documento de Texto OpenDocument)")
        print("4. RTF (Formato Rich Text)")
        print("5. TXT (Texto Simples)")
        print("6. HTML (Página da Web)")
        print("7. EPUB (Publicação Digital)")
        print("8. XLSX (Planilha do Excel)")
        print('')
        format_choice = input("Digite o número correspondente ao formato desejado: ")

        while format_choice not in ('1', '2', '3', '4', '5', '6', '7', '8'):
            print("Escolha inválida. Por favor, escolha um número de 1 a 8.")
            print('')
            format_choice = input("Digite o número correspondente ao formato desejado: ")

        format_map = {
            '1': 'pdf',
            '2': 'docx',
            '3': 'odt',
            '4': 'rtf',
            '5': 'txt',
            '6': 'html',
            '7': 'epub',
            '8': 'xlsx'
        }
        file_extension = format_map.get(format_choice, 'pdf')

        current_directory = os.getcwd()
        file_name = f"{object.get('Name')}.{file_extension}"
        file_path = os.path.join(current_directory, file_name)

        try:
            self._build_command('export', '--mime', f'application/{file_extension}', object.get('Id'),
                   file_path)
            return f"O arquivo foi exportado com sucesso para '{file_path}'."
        except subprocess.CalledProcessError as e:
            return f"Falha ao exportar o arquivo: {e}"

    def download_file(self, object_name: str) -> Optional[str]:
        try:
            object = self._get_nested_object(object_name)

            if object.get('Type') == 'document':
                return self.export_google_doc(object)

            if object.get('Type') == 'folder':
                return self._execute(self._build_command('download', object.get('Id'), '--recursive'))

            return self._execute(self._build_command('download', object.get('Id')))
        except ValueError as e:
            return str(e)

    def upload_file(self, file_path: str, folder_name: Optional[str] = None) -> str:
        file_name = os.path.basename(file_path)
        parent_id = None

        if folder_name:
            try:
                folder = self._get_nested_object(folder_name)
                if folder.get('Type') != 'folder':
                    return f"A pasta de destino '{folder_name}' não foi encontrada."
                parent_id = folder.get('Id')
            except ValueError as e:
                return str(e)

        try:
            existing_file = self._get_object(object_name=file_name, parent_id=parent_id, return_only_id=False)
            if existing_file and existing_file.get('Type') != 'document':
                file_type = "O arquivo" if existing_file.get('Type') == 'regular' else "A pasta"
                return f"O arquivo '{file_name}' já existe na pasta de destino."
        except ValueError:
            pass

        command = self._build_command('upload', file_path)

        if os.path.isdir(file_path):
            command.append('--recursive')
        if parent_id:
            command.extend(['--parent', parent_id])

        result = self._execute(command)
        return "Enviado com sucesso." if result else "Ocorreu um problema. Revise os caminhos do arquivos e tente novamente."

    def update_file(self, object_name: str, file_path: str) -> Optional[str]:
        try:
            object = self._get_nested_object(object_name)
            return self._execute(self._build_command('update', object.get('Id'), file_path))
        except ValueError as e:
            return str(e)

    def delete_file(self, object_name: str) -> Optional[str]:
        try:
            object = self._get_nested_object(object_name)
            confirmation = input(f"Confirme: você quer apagar {object.get('Name')}? [sim/não] ")
            if confirmation.lower() not in ('sim', 's', 'yes', 'y'):
                return "Operação cancelada pelo usuário."

            if object.get('Type') == 'folder':
                return self._execute(self._build_command('delete', object.get('Id'), '--recursive'))
            else:
                result = self._execute(self._build_command('delete', object.get('Id')))
            return "Apagado."
        except ValueError as e:
            return str(e)

def main() -> None:
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('--verbose', action='store_true', help='Enable verbose mode')

    parser = argparse.ArgumentParser(description='Drive no Terminal', parents=[parent_parser])
    subparsers = parser.add_subparsers(dest='command')

    install_parser = subparsers.add_parser('instalar', help='Instalar gdrive', parents=[parent_parser])

    list_parser = subparsers.add_parser('listar', help='Listar arquivos no diretório inicial', parents=[parent_parser])
    list_parser.add_argument('name', nargs='?', help='Nome do arquivo ou pasta para listar')

    search_parser = subparsers.add_parser('pesquisar', help='Pesquisar um arquivo ou pasta pelo nome', parents=[parent_parser])
    search_parser.add_argument('name', help='Nome do arquivo ou pasta para pesquisar')

    download_parser = subparsers.add_parser('baixar', help='Baixar um arquivo ou pasta', parents=[parent_parser])
    download_parser.add_argument('name', help='Nome do arquivo ou pasta para baixar')

    upload_parser = subparsers.add_parser('enviar', help='Enviar um arquivo ou pasta', parents=[parent_parser])
    upload_parser.add_argument('file_path', help='Caminho para o arquivo ou pasta para enviar')
    upload_parser.add_argument('para', nargs='?', choices=['para'], help='Palavra-chave para especificar a pasta (opcional)')
    upload_parser.add_argument('folder_name', nargs='?', help='Nome da pasta de destino (opcional)')

    update_parser = subparsers.add_parser('atualizar', help='Atualizar um arquivo', parents=[parent_parser])
    update_parser.add_argument('name', help='Nome do arquivo para atualizar')
    update_parser.add_argument('com', choices=['com'],help='Palavra-chave para especificar o caminho do novo arquivo')
    update_parser.add_argument('file_path', help='Caminho para o novo arquivo')

    delete_parser = subparsers.add_parser('apagar', help='Apagar um arquivo', parents=[parent_parser])
    delete_parser.add_argument('name', help='Nome do arquivo para apagar')

    args = parser.parse_args()

    gdrive = GDRiveCommand()

    if args.command == 'listar':
        output = gdrive.list_folder(args.name) if args.name else gdrive.list_home()
    elif args.command == 'pesquisar':
        output = gdrive.search_by_name(args.name)
    elif args.command == 'baixar':
        output = gdrive.download_file(args.name)
    elif args.command == 'enviar':
        if args.para and args.folder_name:
            output = gdrive.upload_file(args.file_path, args.folder_name)
        else:
            output = gdrive.upload_file(args.file_path)
    elif args.command == 'atualizar':
        output = gdrive.update_file(args.name, args.file_path)
    elif args.command == 'apagar':
        output = gdrive.delete_file(args.name)
    elif args.command == 'instalar':
        InstallAndConfigure.install_gdrive()
        return
    else:
        parser.print_help()
        return

    print(output)

if __name__ == '__main__':
    main()
