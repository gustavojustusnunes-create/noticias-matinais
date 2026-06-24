import os
import json
from instagrapi import InstaClient

USER = input('Digite seu usuario do Instagram: ')
PASS = input('Digite sua senha: ')

print('Conectando...')
cl = InstaClient()
cl.login(USER, PASS)
cl.get_timeline_feed()

settings = cl.get_settings()
print('\n--- COPIE O TEXTO ABAIXO E COLE NO SECRET INSTAGRAM_SESSION NO GITHUB ---')
print(json.dumps(settings))
print('------------------------------------------------------------------------')

