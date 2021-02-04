from sshtunnel import open_tunnel
from time import sleep

'''
Source: pypi.org/project/sshtunnel/

Alternative Command Line (from pivot box):
python3 -m sshtunnel -U alpha -P password -L :8888 -R 127.0.0.1:8888 -p 22 10.0.0.4

Alternative Command Line (from target box):
ssh -J bravo@10.0.0.175 -L 8888:127:0.0.1:8888 alpha@10.0.0.4
'''

def main():
    with open_tunnel(
    ('10.0.0.4', 22),
    ssh_username="alpha",
    ssh_password="password",
    remote_bind_address=('127.0.0.1', 8888)
    ) as server:
        
        print(server.local_bind_port)
        while True:
            sleep(1)
            
if __name__ == "__main__":
    main()
