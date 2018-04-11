#/bin/bash

USERS=
if [ -n "$2" ] || ! [[ "$1" =~ [0-9][0-9]* ]]; then
  USERS=$@
else
  USERS=`eval echo user{1..${1}}`
fi

if [ -z "${HASH_AUTHENTICATOR_PASS_LEN}" ]; then
  HASH_AUTHENTICATOR_PASS_LEN=6
fi

for u in ${USERS}; do
  echo -n "${u} : "
  hashauthpw --length ${HASH_AUTHENTICATOR_PASS_LEN} ${u} ${HASH_AUTHENTICATOR_SECRET_KEY}
done