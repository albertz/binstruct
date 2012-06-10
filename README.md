binstruct - binary structure serialization
==========================================
https://github.com/albertz/binstruct/
code by Albert Zeyer, www.az2000.de, 2012-06-10
code under BSD

I wanted sth as simple as Python repr or JSON, but:
 - binary data should only add constant overhead
 - very simple format
 - very very big data should be possible
 - searching through the file should be fast
Where the first 2 points were so important for me that
I implemented this format.

Some related formats and the reasons they weren't good
enough for me.
BSON:
 - keys in structs are only C-strings. I want
   any possible data here.
 - already too complicated
Bencode:
 - too restricted, too less formats
OGDL:
 - too simple
...

------- This format. ------------

Bool. Byte \x00 or \x01.

Integers. Use EliasGamma to decode the byte size
of the signed integer. I.e. we start with EliasGamma,
then align that to the next byte and the signed integer
in big endian follows.

Float numbers. Let's keep things simple but let's
also cover a lot of cases.
I use x = (numerator/denominator) * 2^exponent,
where num/denom/exp are all integers.
The binary representation just uses the Integer repr.
If denom=0, with num>0 we get +inf, num=0 we get NaN,
with num<0 we get -inf.

Strings. Just size + string.
If this is a text, please let's all just stick to UTF8.

Lists. Amounts of items, each item as variant.

Dicts. Amounts of items, each item as 2 variants (key+value).

Variants. Bytesize + type-ID-byte + data.
Type-IDs:
 1: list
 2: dict
 3: bool
 4: int
 5: float
 6: str
None has no type-ID. It is just bytesize=0.

File IO

Encryption / decryption. Authorization

Some tests.
