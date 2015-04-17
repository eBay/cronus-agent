# CRONUSAGENT
### An agent automation framework
===========
### Set up Dev Enivronment

**Setting up users and permissions**
    
    add users and groups    
    sudo groupadd -g 61000 app
    sudo useradd -u 78389 cronus -g app
    sudo useradd -u 78402 cronusapp -g app
    sudo sed -i '/cronus/d' /etc/sudoers
    sudo echo '_your_local_user  ALL = (ALL) NOPASSWD: ALL' >>/etc/sudoers
    sudo echo 'cronus  ALL = (ALL) NOPASSWD: ALL' >>/etc/sudoers
    sudo echo 'cronusapp  ALL = (ALL) NOPASSWD: ALL' >>/etc/sudoers

**On Ubuntu**

	sudo apt-get install gcc
	sudo apt-get install swig
	sudo apt-get install ant1.8
	sudo apt-get install python-setuptools
	sudo apt-get install git
	sudo easy_install nested-dict
	(pyopenssl dependency)
	sudo apt-get install libffi-dev 
	sudo apt-get install curl
	(optional: install python2.6 if system does not come with it installed)
	sudo add-apt-repository ppa:fkrull/deadsnakes
	sudo apt-get update
	sudo apt-get install python2.6 python2.6-dev
	(optional: change system default python to python2.6)
	sudo rm /usr/bin/python
	sudo ln -s /usr/bin/python2.6 /usr/bin/python
	python --version

###Build Agent

**build python package**

    cd ~/proj/python-package
    ant depend.resolve package
    ant -Dbuildnum=1 depend.resolve package (build with options)
python package is in /target/dist as a cronus package

**build agent package**

    cd ~/proj/agent
    ant depend.resolve package
    ant -Dbuildnum=1 -Dnotest=true -Dnopylint=true depend.resolve package (build with options)
agent and agent config package are in /target/dist as cronus packages
 
###Deploy Agent
**Deploy agent locally**

	cp agent-{pkg_ver}.unix.cronus /proj/agent/scripts/agent_install
    cp agent_config-{pkg_ver}.unix.cronus /proj/agent/scripts/agent_install
    cp python_package-{pypkg_ver}.unix.cronus /proj/agent/scripts/agent_install
    cat agent_install | pkg_ver={pkg_ver} pypkg_ver={pypkg_ver} target_dir={dir} bash

**Deploy agent remotely**

    curl -sS 'https://raw.githubusercontent.com/yubin154/cronusagent/master/agent/scripts/agent_install/install_agent' | sudo pkgver={agent_version} target_dir={install_dir} bash





