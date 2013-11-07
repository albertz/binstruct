binstruct - binary structure serialization
------------------------------------------
https://github.com/albertz/binstruct/,

Copyright (c) 2012, Albert Zeyer, www.az2000.de
All rights reserved.
file created 2012-06-10

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met: 

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer. 
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution. 

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

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

More, without details:
* CBOR ([RFC](http://tools.ietf.org/html/rfc7049), [HN discussion](https://news.ycombinator.com/item?id=6632576))
* msgpack
* Google's Protocol Buffers
* [Apache (Facebook) Thrift](http://thrift.apache.org/)

## This format.

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

Lists. Amount of items, each item as variant.

Dicts. Amount of items, each item as 2 variants (key+value).

Variants. Bytesize + type-ID-byte + data.
Type-IDs:
* 1: list
* 2: dict
* 3: bool
* 4: int
* 5: float
* 6: str

None has no type-ID. It is just bytesize=0.

## Additional functions

File IO

Encryption / decryption. Authorization

Some tests.

Some RPython tests.
For RPython lang def, see: http://doc.pypy.org/en/latest/coding-guide.html#rpython-definition
