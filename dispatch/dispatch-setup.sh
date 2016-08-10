#!/bin/bash
# Chuck Rolke 2015

#
# Set up proton and qpid for a dispatch test run.
#
# Usage:
#  > ./dispatch_setup.sh
#  > ./dispatch_setup.sh build
#
# A blank arg 1 just sets the enviornment. Remember to dot source it!
# A non-blank arg 1 performs a complete rebuild.
#
# And then with the environment set up run dispatch in kdevelop:
#  > kdevelop &
# Run qdrouterd with:
#  Project Target : qpid-dispatch/router/qdrouterd
#  Executable     : /home/<>/git/qpid-dispatch
#  Arguments      : -c /home/<>/test-router.conf -I /home/<>/git/qpid-dispatch/python
#  Working Dir    : /home/<>/git/qpid-dispatch/build
#
export        PROTON=~/git/qpid-proton
export    QPIDPYTHON=~/git/qpid-python
export       QPIDCPP=~/git/qpid-cpp
export      DISPATCH=~/git/qpid-dispatch
export INSTALLPREFIX=/opt/local

build_log () {
    dir=$1
    file=${dir}/builds.txt
    mkdir -p ${dir}
    echo ====                               >> ${file}
    date                                    >> ${file}
    echo `pwd`                              >> ${file}
    git rev-parse --symbolic-full-name HEAD >> ${file}
    git rev-parse HEAD                      >> ${file}
}

merge_paths() {
    # Merge paths, remove duplicates (keep first instance)
    path=$(echo $* | sed 's/:/ /'g) # Split with spaces.
    newpath=""
    for d in $path; do		# Remove duplicates
	{ echo $newpath | egrep -q "$d"; } || newpath="$newpath:$d"
    done
    echo $newpath | sed 's/^://' # Remove leading :
}

if [ ! -z "$1" ]; then
    # Go somewhere safe
    cd ~

    # Flush old builds
    rm -rf ${INSTALLPREFIX}
    rm -rf ${PROTON}/build
    rm -rf ${QPIDCPP}/build
    rm -rf ${DISPATCH}/build
    mkdir ${PROTON}/build
    mkdir ${QPIDCPP}/build
    mkdir ${DISPATCH}/build
    
    # build proton
    cd ${PROTON}/build
    build_log ${INSTALLPREFIX}
    cmake -DCMAKE_BUILD_TYPE=Debug -DCMAKE_INSTALL_PREFIX=${INSTALLPREFIX} ..
    make -j 8 install

    # install python
    cd ${QPIDPYTHON}
    python setup.py install --prefix=${INSTALLPREFIX}
    
    # build qpid
    cd ${QPIDCPP}/build
    build_log ${INSTALLPREFIX}
    cmake -DCMAKE_BUILD_TYPE=Debug -DCMAKE_INSTALL_PREFIX=${INSTALLPREFIX} -DBUILD_DOCS=No ..
    make -j 8 install

    # install qpid giblets
#   cd ${QPID}/qpid/tools;      ./setup.py install --prefix ${INSTALLPREFIX} # Broke on 2016-05-17
#   cd ${QPID}/qpid/python;     ./setup.py install --prefix ${INSTALLPREFIX} # Skipped on 5-17 for debug
#   cd ${QPID}/qpid/extras/qmf; ./setup.py install --prefix ${INSTALLPREFIX} # Broke on 2016-??-??

    # build dispatch
    cd ${DISPATCH}/build
    build_log ${INSTALLPREFIX}
    cmake -G "Eclipse CDT4 - Unix Makefiles" -DCMAKE_BUILD_TYPE=Debug -DCMAKE_INSTALL_PREFIX=${INSTALLPREFIX} ..
    # Don't install. This allows running from build area.
    make -j 8

    cd ${DISPATCH}/build
fi

# set up the environment
export PATH=$(merge_paths \
		  ${DISPATCH}/build \
		  ${DISPATCH}/build/tests \
		  ${DISPATCH}/build/router \
		  ${DISPATCH}/tools \
		  ${DISPATCH}/build/tools \
		  ${DISPATCH}/bin \
		  ~/bin \
		  ${INSTALLPREFIX}/sbin \
		  ${INSTALLPREFIX}/bin \
		  ${PATH})
export PYTHONPATH=$(merge_paths \
			${DISPATCH}/python \
			${DISPATCH}/build/python \
			${DISPATCH}/tests \
			${DISPATCH}/build \
			${INSTALLPREFIX}/lib/proton/bindings/python \
                        ${INSTALLPREFIX}/lib64/proton/bindings/python \
                        ${INSTALLPREFIX}/lib/python2.7/site-packages \
			${INSTALLPREFIX}/lib64/python2.7/site-packages \
			/usr/lib64/python27.zip \
			/usr/lib64/python2.7 \
			/usr/lib64/python2.7/plat-linux2 \
			/usr/lib64/python2.7/lib-tk \
			/usr/lib64/python2.7/lib-old \
			/usr/lib64/python2.7/lib-dynload \
			/usr/lib64/python2.7/site-packages \
			/usr/lib64/python2.7/site-packages/gtk-2.0 \
			/usr/lib/python2.7/site-packages \
		        ${PYTHONPATH})
export LD_LIBRARY_PATH=$(merge_paths \
			     ${INSTALLPREFIX}/lib64 \
			     ${LD_LIBRARY_PATH})
export BUILD_DIR=${DISPATCH}/build
export QPID_DISPATCH_HOME=${DISPATCH}
export QPID_DISPATCH_LIB=${DISPATCH}/build/src/libqpid-dispatch.so
export MANPATH=$(merge_paths \
		     ${DISPATCH}/build/doc/man \
		     ${MANPATH})
export SOURCE_DIR=${DISPATCH}
