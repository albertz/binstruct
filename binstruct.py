# binstruct - binary structure serialization
# ------------------------------------------
# https://github.com/albertz/binstruct/,


# Copyright (c) 2012, Albert Zeyer, www.az2000.de
# All rights reserved.
# file created 2012-06-10


# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met: 
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer. 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution. 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


# I wanted sth as simple as Python repr or JSON, but:
#  - binary data should only add constant overhead
#  - very simple format
#  - very very big data should be possible
#  - searching through the file should be fast

# Where the first 2 points were so important for me that
# I implemented this format.

# Some related formats and the reasons they weren't good
# enough for me.

# BSON:
#  - keys in structs are only C-strings. I want
#    any possible data here.
#  - already too complicated

# Bencode:
#  - too restricted, too less formats

# OGDL:
#  - too simple
# ...

# More, without details:
# * CBOR ([RFC](http://tools.ietf.org/html/rfc7049), [HN discussion](https://news.ycombinator.com/item?id=6632576))
# * msgpack
# * Google's Protocol Buffers
# * [Apache (Facebook) Thrift](http://thrift.apache.org/)

### This format.

FILESIGNATURE = "BINSTRUCT.1\x00"
FILESIGNATURE_CRYPTED = "BINSTRUCT.CRYPTED.1\x00"
class FormatError(Exception): pass
from array import array
from StringIO import StringIO

# Bool. Byte \x00 or \x01.

def boolEncode(b): return array("B", (b,))
def boolDecode(stream): return bool(ord(stream.read(1)))

# Integers. Use EliasGamma to decode the byte size
# of the signed integer. I.e. we start with EliasGamma,
# then align that to the next byte and the signed integer
# in big endian follows.

def bitsOf(n):
	assert n >= 0
	if n == 0: return 0
	return len(bin(n)) - 2

def bitListToInt(l):
	i = 0
	bitM = 1
	for bit in reversed(l):
		i += bitM * int(bit)
		bitM <<= 1
	return i

def bitListToBin(l):
	bin = array("B", (0,)) * (len(l) / 8)
	for i in range(0, len(l), 8):
		byte = bitListToInt(l[i:i+8])
		bin[i/8] = byte
	return bin

def eliasGammaEncode(n):
	assert n > 0
	bitLen = bitsOf(n)
	binData = [False] * (bitLen - 1) # prefix
	bit = 1 << (bitLen - 1)
	while bit > 0:
		binData += [bool(n & bit)]
		bit >>= 1
	binData += [False] * (-len(binData) % 8) # align by 8
	return bitListToBin(binData)

def eliasGammaDecode(stream):
	def readBits():
		while True:
			byte = ord(stream.read(1))
			bitM = 1 << 7
			while bitM > 0:
				yield bool(byte & bitM)
				bitM >>= 1
	num = 0
	state = 0
	bitM = 1
	for b in readBits():
		if state == 0:
			if not b:
				bitM <<= 1
				continue
			state = 1
		num += bitM * int(b)
		bitM >>= 1
		if bitM == 0: break
	return num

def intToBin(x):
	bitLen = bitsOf(x) if (x >= 0) else bitsOf(abs(x+1)) # two-complement
	bitLen += 1 # for the sign
	byteLen = (bitLen+7) / 8
	bin = array("B", (0,)) * byteLen
	if x < 0:
		x += 1 << (byteLen * 8)
		assert x > 0
	for i in range(byteLen):
		bin[byteLen-i-1] = (x >> (i * 8)) & 255
	return bin

def binToInt(bin):
	if isinstance(bin, str): bin = array("B", bin)
	n = 0
	byteLen = len(bin)
	for i in range(byteLen):
		n += bin[byteLen-i-1] << (i * 8)
	if n >= 1 << (byteLen*8 - 1):
		n -= 1 << (byteLen * 8)
	return n

def intEncode(x):
	bin = intToBin(x)
	assert len(bin) > 0
	gammaBin = eliasGammaEncode(len(bin))
	return gammaBin + bin

def intDecode(stream):
	if isinstance(stream, array): stream = stream.tostring()
	if isinstance(stream, str): stream = StringIO(stream)
	binLen = eliasGammaDecode(stream)
	return binToInt(stream.read(binLen))

# Float numbers. Let's keep things simple but let's
# also cover a lot of cases.
# I use x = (numerator/denominator) * 2^exponent,
# where num/denom/exp are all integers.
# The binary representation just uses the Integer repr.
# If denom=0, with num>0 we get +inf, num=0 we get NaN,
# with num<0 we get -inf.

def floatEncode(x):
	import math
	from fractions import Fraction
	from decimal import Decimal
	if math.isnan(x): return intEncode(0) * 3
	if math.isinf(x): return intEncode(math.copysign(1, x)) + intEncode(0) * 2
	if isinstance(x, Decimal):
		sign,digits,base10e = x.as_tuple()
		e = 0
		num = digits
		denom = 10 ** -base10e
	elif isinstance(x, Fraction):
		e,num,denom = 0, x.numerator, x.denominator
	else:
		m,e = math.frexp(x)
		num,denom = m.as_integer_ratio()
	return intEncode(num) + intEncode(denom) + intEncode(e)

def floatDecode(stream):
	if isinstance(stream, array): stream = stream.tostring()
	if isinstance(stream, str): stream = StringIO(stream)
	num,denom,e = intDecode(stream),intDecode(stream),intDecode(stream)
	return (float(num)/denom) * (2 ** e)

# Strings. Just size + string.
# If this is a text, please let's all just stick to UTF8.

def strEncode(s):
	if isinstance(s, str): s = array("B", s)
	if isinstance(s, unicode): s = array("B", s.encode("utf-8"))
	return intEncode(len(s)) + s

def strDecode(stream):
	if isinstance(stream, array): stream = stream.tostring()
	if isinstance(stream, str): stream = StringIO(stream)
	strLen = intDecode(stream)
	return stream.read(strLen)

# Lists. Amount of items, each item as variant.

def listEncode(l):
	bin = intEncode(len(l))
	for item in l:
		bin += varEncode(item)
	return bin	

def listDecode(stream):
	listLen = intDecode(stream)
	l = [None]*listLen
	for i in range(listLen):
		l[i] = varDecode(stream)
	return l	

# Dicts. Amount of items, each item as 2 variants (key+value).

def dictEncode(d):
	bin = intEncode(len(d))
	for key,value in sorted(d.items()):
		bin += varEncode(key)
		bin += varEncode(value)
	return bin

class Dict(dict):
	def __getattr__(self, key):
		try: return dict.__getitem__(self, key)
		except KeyError: raise AttributeError
	def __setattr__(self, key, value):
		return dict.__setitem__(self, key, value)

def dictDecode(stream):
	dictLen = intDecode(stream)
	d = Dict()
	for i in range(dictLen):
		key = varDecode(stream)
		value = varDecode(stream)
		d[key] = value
	return d

# Variants. Bytesize + type-ID-byte + data.
# Type-IDs:
# * 1: list
# * 2: dict
# * 3: bool
# * 4: int
# * 5: float
# * 6: str

# None has no type-ID. It is just bytesize=0.

def prefixWithSize(data):
	return intEncode(len(data)) + data
	
def varEncode(v):
	from numbers import Integral, Real
	from collections import Mapping, Sequence
	if v is None: return intEncode(0)
	if isinstance(v, bool):
		return prefixWithSize(array("B", (3,)) + boolEncode(v))
	if isinstance(v, Integral):
		return prefixWithSize(array("B", (4,)) + intEncode(v))
	if isinstance(v, Real):
		return prefixWithSize(array("B", (5,)) + floatEncode(v))
	if isinstance(v, (str,unicode,array)):
		return prefixWithSize(array("B", (6,)) + strEncode(v))
	if isinstance(v, Mapping):
		data = dictEncode(v)
		typeEncoded = array("B", (2,))
		lenEncoded = intEncode(len(data) + 1)
		return lenEncoded + typeEncoded + data
	if isinstance(v, Sequence):
		data = listEncode(v)
		typeEncoded = array("B", (1,))
		lenEncoded = intEncode(len(data) + 1)
		return lenEncoded + typeEncoded + data
	assert False, "type of " + repr(v) + " cannot be encoded"

def varDecode(stream):
	if isinstance(stream, array): stream = stream.tostring()
	if isinstance(stream, str): stream = StringIO(stream)
	varLen = intDecode(stream)
	if varLen < 0: raise FormatError("varLen < 0")
	if varLen == 0: return None
	type = ord(stream.read(1))
	if type == 1: return listDecode(stream)
	if type == 2: return dictDecode(stream)
	if type == 3: return boolDecode(stream)
	if type == 4: return intDecode(stream)
	if type == 5: return floatDecode(stream)
	if type == 6: return strDecode(stream)
	raise FormatError("type %i unknown" % type)

### Additional functions

# File IO

def write(file, v):
	if isinstance(file, (str,unicode)): file = open(file, "wb")
	file.write(FILESIGNATURE)
	file.write(varEncode(v).tostring())
	return file

def read(file):
	if isinstance(file, (str,unicode)): file = open(file, "rb")
	sig = file.read(len(FILESIGNATURE))
	if sig != FILESIGNATURE: raise FormatError("file signature wrong")
	return varDecode(file)

# Encryption / decryption. Authorization

def randomString(l):
	import random
	return ''.join(chr(random.randint(0, 0xFF)) for i in range(l))

def genkeypair():
	from Crypto.PublicKey import RSA
	key = RSA.generate(2048)
	pubkey = key.publickey().exportKey("DER")
	privkey = key.exportKey("DER")
	return (pubkey,privkey)
	
def encrypt(v, encrypt_rsapubkey=None, sign_rsaprivkey=None):
	from Crypto.PublicKey import RSA
	from Crypto.Cipher import PKCS1_OAEP
	from Crypto.Cipher import AES
	from Crypto.Signature import PKCS1_PSS
	from Crypto.Hash import SHA512
	out = {}
	if encrypt_rsapubkey:
		encrypt_rsapubkey = RSA.importKey(encrypt_rsapubkey)
		rsa = PKCS1_OAEP.new(encrypt_rsapubkey)
		aeskey = randomString(32)
		iv = randomString(16)
		aes = AES.new(aeskey, AES.MODE_CBC, iv)
		data = varEncode(v).tostring()
		data += "\x00" * (-len(data) % 16)
		out["aesInfo"] = rsa.encrypt(aeskey + iv)
		out["data"] = aes.encrypt(data)
		out["encrypted"] = True
	else:
		out["data"] = varEncode(v).tostring()
		out["encrypted"] = False
	if sign_rsaprivkey:
		sign_rsaprivkey = RSA.importKey(sign_rsaprivkey)
		pss = PKCS1_PSS.new(sign_rsaprivkey)
		h = SHA512.new()
		h.update(out["data"])
		sign = pss.sign(h)
		out["signature"] = sign
	else:
		out["signature"] = None
	return out

def verifyData(data, sign, verifysign_rsapubkey):
	from Crypto.PublicKey import RSA
	from Crypto.Signature import PKCS1_PSS
	from Crypto.Hash import SHA512
	h = SHA512.new()
	h.update(data)
	verifysign_rsapubkey = RSA.importKey(verifysign_rsapubkey)
	pss = PKCS1_PSS.new(verifysign_rsapubkey)
	if not pss.verify(h, sign):
		raise FormatError("signature is not authentic")		
	
def decrypt(data, decrypt_rsaprivkey=None, verifysign_rsapubkey=None):
	from Crypto.PublicKey import RSA
	from Crypto.Cipher import PKCS1_OAEP
	from Crypto.Cipher import AES
	if data["encrypted"]:
		if not decrypt_rsaprivkey: raise FormatError("data is encrypted, key missing")
		decrypt_rsaprivkey = RSA.importKey(decrypt_rsaprivkey)
		rsa = PKCS1_OAEP.new(decrypt_rsaprivkey)
		aesdata = rsa.decrypt(data["aesInfo"])
		aeskey = aesdata[0:32]
		iv = aesdata[32:]
		aes = AES.new(aeskey, AES.MODE_CBC, iv)
		outdata = aes.decrypt(data["data"])
	else:
		outdata = data["data"]
	if verifysign_rsapubkey:
		sign = data["signature"]
		if not sign: raise FormatError("signature missing")
		verifyData(data["data"], sign, verifysign_rsapubkey)
	return varDecode(outdata)

def writeEncrypt(file, v, encrypt_rsapubkey=None, sign_rsaprivkey=None):
	if isinstance(file, (str,unicode)): file = open(file, "wb")
	file.write(FILESIGNATURE_CRYPTED)	
	file.write(varEncode(encrypt(v, encrypt_rsapubkey, sign_rsaprivkey)).tostring())
	return file

def readDecrypt(file, decrypt_rsaprivkey=None, verifysign_rsapubkey=None):
	if isinstance(file, (str,unicode)): file = open(file, "rb")
	sig = file.read(len(FILESIGNATURE_CRYPTED))
	if sig != FILESIGNATURE_CRYPTED: raise FormatError("file signature wrong")
	return decrypt(varDecode(file), decrypt_rsaprivkey, verifysign_rsapubkey)

def verifyFile(file, verifysign_rsapubkey):
	if isinstance(file, (str,unicode)): file = open(file, "rb")
	sig = file.read(len(FILESIGNATURE_CRYPTED))
	if sig != FILESIGNATURE_CRYPTED: raise FormatError("file signature wrong")
	data = varDecode(file)
	sign = data["signature"]
	if not sign: raise FormatError("signature missing")
	verifyData(data["data"], sign, verifysign_rsapubkey)
	

# Some tests.

def test_crypto():
	v = {"hello":"world", 1:False, 42:-2**1024, "foo":None, "bar":[0.5,1,None,1.345,[]]}
	pub1,priv1 = genkeypair()
	pub2,priv2 = genkeypair()
	pub3,priv3 = genkeypair()
	
	encrypted_signed = encrypt(v, pub1, priv2)
	decrypted1 = decrypt(encrypted_signed, priv1)
	decrypted2 = decrypt(encrypted_signed, priv1, pub2)
	assert v == decrypted1, repr(v) + " != " + repr(decrypted1)
	assert v == decrypted2, repr(v) + " != " + repr(decrypted2)
	try:
		decrypt(encrypted_signed, priv1, pub3)
		assert False, "signature wrongly assumed authentic (1)"
	except FormatError: pass
	
	just_signed = encrypt(v, sign_rsaprivkey=priv1)
	decrypted1 = decrypt(just_signed, priv2)
	decrypted2 = decrypt(just_signed, priv2, pub1)
	assert v == decrypted1, repr(v) + " != " + repr(decrypted1)
	assert v == decrypted2, repr(v) + " != " + repr(decrypted2)
	try:
		decrypt(encrypted_signed, priv1, pub3)
		assert False, "signature wrongly assumed authentic (2)"
	except FormatError: pass
	

def test():
	# bitsOf
	for (arg, res) in [(0,0), (255,8), (256,9), (1<<1000-1,1000)]:
		assert bitsOf(arg) == res
	
	# bitListToInt
	for (arg, res) in [([1,0,0,0],8)]:
		assert bitListToInt(arg) == res
	
	# eliasGammaEncode + decode
	for (value, raw) in [
		(1, '\x80'),
		(255, '\x01\xfe'),
		(127, '\x03\xf8'),
		(16, '\x08\x00'),
		(8, '\x10'),
		(15, '\x1e')
	]:
		assert eliasGammaEncode(value).tostring() == raw
		assert eliasGammaDecode(StringIO(raw)) == value
		
	# varEncode + decode
	for (value, raw) in [
		(42, '\x80\x03\x04\x80*'),
		("hello", '\x80\x08\x06\x80\x05hello'),
		([1,False,-1,0.5,"hi",{2:3}],
			'\x800\x01\x80\x06\x80\x03\x04\x80\x01\x80\x02' +
			'\x03\x00\x80\x03\x04\x80\xff\x80\x07\x05\x80' +
			'\x01\x80\x02\x80\x00\x80\x05\x06\x80\x02hi\x80' +
			'\r\x02\x80\x01\x80\x03\x04\x80\x02\x80\x03\x04\x80\x03'),
	]:
		assert varEncode(value).tostring() == raw
		assert varDecode(StringIO(raw)) == value


# Some RPython tests.
# For RPython lang def, see: http://doc.pypy.org/en/latest/coding-guide.html#rpython-definition

def main(argv):
	print "Hello!"
	print "args:", argv
	print "%r" % varEncode(argv)
	test()
	print "Bye!"

def target(driver, args):
	"""
	Target function for RPython.
	"""
	return main, None

if __name__ == '__main__':
	test()
	print "tests passed"

