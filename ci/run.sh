#!/bin/sh

SCRIPT=$(readlink -f "$0")
BASE=$(dirname "$SCRIPT")

CI_STATUS=0
CI_UNITTEST="failing"
CI_COVERAGE="0"
CI_PYLINT="0"

coverage run -m unittest discover -v $BASE

if [ "$?" -eq "0" ]; then
  CI_UNITTEST="passing"
else
  echo "Unittests failed"
  CI_STATUS=1
fi

OUTPUT=$(coverage report --include=$BASE/../lib/*/*.py,$BASE/../lib/*.py -m)

echo "$OUTPUT"

CI_COVERAGE=$(echo "$OUTPUT" | tail -n 1 | awk '{print $4}' | tr -d '%')

if [ "$CI_COVERAGE" -lt "60" ]; then
  echo "Coverage below 60"
  CI_STATUS=2
fi

OUTPUT=$(pylint --rcfile=$BASE/.pylintrc $BASE/../*/*.py $BASE/../*.py $BASE/../bin/*.py $BASE/../ci/*.py $BASE/../ci/*/*.py 2>/dev/null)
#OUTPUT=$(find $BASE/../ -name '*.py' | xargs pylint --rcfile=$BASE/.pylintrc 2>/dev/null)

echo "$OUTPUT"

CI_PYLINT=$(echo "$OUTPUT" | grep "Your code" | sed -n "s/Your code has been rated at \(\S*\)\.\S*\/10.*$/\1/p")

if [ "$CI_PYLINT" -lt "10" ]; then
  echo "PyLint below 10"
  CI_STATUS=3
fi


exit $CI_STATUS
