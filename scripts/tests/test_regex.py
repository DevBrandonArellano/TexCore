import re

pat = re.compile(r'^(export|vendedores|gerencial)(/[a-zA-Z0-9_-]+)*$')
print("Match:", bool(pat.match("vendedores/1/ventas")))
