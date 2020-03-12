import asyncio
import os,subprocess


def beautify(output):
    return output.decode().strip()

def bash_command(cmd):
    subprocess.Popen(cmd, shell=True)


def main():
    bash_command('git fetch')
    var_local = subprocess.check_output('cat .git/refs/heads/master',shell=True)
    var_remote = subprocess.check_output('git log origin/master -1 | head -n1 | cut -d" " -f2',shell=True)

    if (beautify(var_local)) != (beautify(var_remote)):
        bash_command('git pull')
        print('Updated needed')
    else:
        print('Already on current version')

if __name__ == "__main__":
    main()