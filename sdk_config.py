#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Configurazione SDK NAOqi / Choregraphe.

Aggiunge automaticamente il path della libreria Choregraphe a sys.path
in modo che 'import qi' e 'from naoqi import ALProxy' funzionino.

Importare questo modulo PRIMA di qualsiasi import qi/naoqi:
    import sdk_config
    import qi
"""

from __future__ import print_function
import os
import sys
import struct


def _bits_python():
    return struct.calcsize("P") * 8


# Path dell'SDK di Choregraphe (modifica se necessario)
_CHOREGRAPHE_PATHS = [
    # Windows - installazione standard
    r"C:\Program Files (x86)\Aldebaran Robotics\Choregraphe Suite 2.1\lib",
    r"C:\Program Files\Aldebaran Robotics\Choregraphe Suite 2.1\lib",
    # Variabili d'ambiente personalizzate
    os.environ.get("NAOQI_SDK_PATH", ""),
    os.environ.get("CHOREGRAPHE_LIB", ""),
]

# Porta di default per Choregraphe (sovrascrivibile con env var)
DEFAULT_PORT = int(os.environ.get("NAO_PORT", "9559"))

_sdk_found = False

for _path in _CHOREGRAPHE_PATHS:
    if _path and os.path.isdir(_path) and _path not in sys.path:
        sys.path.insert(0, _path)
        # Verifica che il modulo sia effettivamente importabile
        try:
            import qi as _qi_test
            _sdk_found = True
            print("[SDK] Trovato qi in: {}".format(_path))
            break
        except ImportError:
            # Path trovato ma qi non caricabile (architettura sbagliata?)
            pass

if not _sdk_found:
    print("[SDK WARN] SDK Choregraphe non trovato automaticamente.")
    print("[SDK WARN] Python {} {} bit".format(sys.version.split()[0], _bits_python()))
    print("[SDK WARN] Imposta NAOQI_SDK_PATH con il percorso della cartella lib dell'SDK.")
    print("[SDK WARN] Es: set NAOQI_SDK_PATH=C:\\...\\Choregraphe Suite 2.1\\lib")
