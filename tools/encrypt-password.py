#!/bin/env python3

import bcrypt
from getpass import getpass

password = getpass()

print(bcrypt.hashpw(password.encode('UTF-8'), bcrypt.gensalt()).decode())

