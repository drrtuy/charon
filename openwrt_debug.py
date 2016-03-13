from binascii import hexlify,  unhexlify
from hashlib import md5
from itertools import cycle

def xorString(message, key):
    #for c,k in zip(message, cycle(key) ):
    #    print "c",ord(c),"\tk",ord(k),"result", ord(c) ^ ord(k)
    cyphered = ''.join( chr (ord(c) ^ ord(k) ) for c,k in zip(message, cycle(key) ) )
    return cyphered

openwrtSecret = 'shopster'
passw = '1234\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
c = unhexlify( '68369418ad141e43809cfa0a981c6f31' )
challWithSecret =  md5( '{}{}'.format( c, openwrtSecret ) ).digest()
print  challWithSecret
xorString( passw, challWithSecret)
hashedPass = xorString( passw, challWithSecret )
print hexlify(hashedPass)

print '{:0x00>32}'.format(passw)


http://dev.zerothree.su/preuath/?res=notyet&uamip=192.168.182.1&uamport=3990&challenge=7236a55bca0afc59a033da4794bc1695&called=90-F6-52-5B-73-F4&mac=24-0A-64-94-A3-A1&ip=192.168.182.2&nasid=nas01&sessionid=56af2e1d00000001&userurl=http%3a%2f%2fya.ru

http://192.168.182.1:3990/logon?username=24-0A-64-94-A3-A1&password=Q%00z%0B%04%5D%06%23
7236a55bca0afc59a033da4794bc1695

https://lobster.zerothree.su/hotspotlogin.php?res=success&uamip=192.168.182.1&uamport=3990&called=90-F6-52-5B-73-F4&uid=Puser&mac=24-0A-64-94-A3-A1&ip=192.168.182.2&nasid=nas01&sessionid=56e25a6200000001&userurl=http%3a%2f%2fya.ru%2f&md=9FAF44B2A75B1122C11FBCA4A6195BFC

<?php
$challenge = '68369418ad141e43809cfa0a981c6f31';
$uamsecret = 'shopster';
$password = '1234';
$hexchal = pack ("H32", $challenge);
$newchal = pack ("H*", md5($hexchal . $uamsecret));
#echo unpa($newchal);

function unpa($stra) {
    return implode ("", unpack("H32", $stra)); 
}
  $newpwd = pack("a32", $password);
  #echo unpa($newpwd);
  $b = $newpwd[0] ^ $newchal[0];
  echo ord($newpwd[0]). "\n";
  echo ord($newchal[0]). "\n";
  echo ord($b)."\n";
  $pappassword = implode ("", unpack("H32", ($newpwd ^ $newchal)));
  echo $pappassword;
