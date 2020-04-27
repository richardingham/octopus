import os
from os.path import join as pjoin
from distutils.dir_util import mkpath

from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend

from octopus.blocktopus.database.createdb import createdb

if __name__ == "__main__":
    DATA_DIR = pjoin(os.getcwd(), 'data')

    print ("Creating Data Directories")
    mkpath(pjoin(DATA_DIR, 'sketches'))
    mkpath(pjoin(DATA_DIR, 'experiments'))
    mkpath(pjoin(DATA_DIR, 'ssh-keys'))

    createdb(DATA_DIR)

    print ("Creating SSH Keys")
    KEY = rsa.generate_private_key(
        backend=crypto_default_backend(),
        public_exponent=65537,
        key_size=2048
    )

    with open(pjoin(DATA_DIR, 'ssh-keys', 'ssh_host_rsa_key.pub'), 'wb') as f:
        f.write(KEY.public_key().public_bytes(
            crypto_serialization.Encoding.OpenSSH,
            crypto_serialization.PublicFormat.OpenSSH
        ))

    with open(pjoin(DATA_DIR, 'ssh-keys', 'ssh_host_rsa_key'), 'wb') as f:
        f.write(KEY.private_bytes(
            crypto_serialization.Encoding.PEM,
            crypto_serialization.PrivateFormat.TraditionalOpenSSL,
            crypto_serialization.NoEncryption()
        ))

    print ("")
    print ("Public SSH key is located at: " + pjoin(DATA_DIR, 'ssh-keys', 'ssh_host_rsa_key.pub'))
    print ("Use this key for SSH connections to the console.")
