USERS=
if [ -n "$2" ] || ! [[ "$2" =~ [0-9]* ]]; then
  USERS=$@
else
  USERS=`eval echo user{1..${1}}`
fi

for u in ${USERS}; do
  echo -n "${u} : "
  hashauthpw --length 10 ${u} ${HASH_AUTHETICATOR_SECRET_KEY}
done