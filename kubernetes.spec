%global debug_package   %{nil}
%global provider        github
%global provider_tld    com
%global project	        openshift
%global repo            origin
# https://github.com/openshift/origin
%global provider_prefix	%{provider}.%{provider_tld}/%{project}/%{repo}
%global import_path     k8s.io/kubernetes
%global commit		a41c9ff38d52fd508481c3c2bac13d52871fde02
%global shortcommit	%(c=%{commit}; echo ${c:0:7})

%global openshift_ip    github.com/openshift/origin

%global k8s_provider        github
%global k8s_provider_tld    com
%global k8s_project         kubernetes
%global k8s_repo            kubernetes
# https://github.com/kubernetes/kubernetes
%global k8s_provider_prefix %{k8s_provider}.%{k8s_provider_tld}/%{k8s_project}/%{k8s_repo}
%global k8s_commit      4c8e6f47ec23f390978e651232b375f5f9cde3c7
%global k8s_shortcommit %(c=%{k8s_commit}; echo ${c:0:7})
%global k8s_src_dir     Godeps/_workspace/src/k8s.io/kubernetes/
%global k8s_src_dir_sed Godeps\\/_workspace\\/src\\/k8s\\.io\\/kubernetes\\/

%global con_provider        github
%global con_provider_tld    com
%global con_project         kubernetes
%global con_repo            contrib
# https://github.com/kubernetes/kubernetes
%global con_provider_prefix %{con_provider}.%{con_provider_tld}/%{con_project}/%{con_repo}
%global con_commit      1c4eb2d56c70adfb2eda7c7d2543b40274d5ede8
%global con_shortcommit %(c=%{con_commit}; echo ${c:0:7})

%global O4N_GIT_MAJOR_VERSION 1
%global O4N_GIT_MINOR_VERSION 1
%global O4N_GIT_VERSION       v1.1
%global K8S_GIT_VERSION       v1.1.0-origin-1107-g4c8e6f4

#I really need this, otherwise "version_ldflags=$(kube::version_ldflags)"
# does not work
%global _buildshell	/bin/bash
%global _checkshell	/bin/bash

Name:		kubernetes
Version:	1.1.0
Release:	0.3.origin.git%{k8s_shortcommit}%{?dist}
Summary:        Container cluster management
License:        ASL 2.0
URL:            %{import_path}
ExclusiveArch:  x86_64
Source0:        https://%{provider_prefix}/archive/%{commit}/%{repo}-%{shortcommit}.tar.gz
Source1:        https://%{k8s_provider_prefix}/archive/%{k8s_commit}/%{k8s_repo}-%{k8s_shortcommit}.tar.gz
Source2:        https://%{con_provider_prefix}/archive/%{con_commit}/%{con_repo}-%{con_shortcommit}.tar.gz

Source33:        genmanpages.sh

Patch2:         Change-etcd-server-port.patch

Patch4:         internal-to-inteernal.patch
Patch5:         0001-internal-inteernal.patch

# k8s uses default cluster if not specified, o4n does not
Patch7:         do-not-unset-default-cluster.patch

Patch8:         add-missing-short-option-for-server.patch
Patch9:         hack-test-cmd.sh.patch
# Due to k8s 5d08dcf8377e76f2ce303dc79404f511ebef82e3
Patch10:        keep-solid-port-for-kube-proxy.patch

# It obsoletes cadvisor but needs its source code (literally integrated)
Obsoletes:      cadvisor

# kubernetes is decomposed into master and node subpackages
# require both of them for updates
Requires: kubernetes-master = %{version}-%{release}
Requires: kubernetes-node = %{version}-%{release}

%description
%{summary}

%package unit-test
Summary: %{summary} - for running unit tests

Requires: etcd >= 2.0.9

%description unit-test
%{summary} - for running unit tests

%package master
Summary: Kubernetes services for master host

BuildRequires: golang >= 1.2-7
BuildRequires: systemd
BuildRequires: rsync
BuildRequires: go-md2man

Requires(pre): shadow-utils
Requires: kubernetes-client = %{version}-%{release}

# if node is installed with node, version and release must be the same
Conflicts: kubernetes-node < %{version}-%{release}
Conflicts: kubernetes-node > %{version}-%{release}

%description master
Kubernetes services for master host

%package node
Summary: Kubernetes services for node host

%if 0%{?fedora} >= 21 || 0%{?rhel}
Requires: docker
%else
Requires: docker-io
%endif

BuildRequires: golang >= 1.2-7
BuildRequires: systemd
BuildRequires: rsync
BuildRequires: go-md2man

Requires(pre): shadow-utils
Requires: socat
Requires: kubernetes-client = %{version}-%{release}

# if master is installed with node, version and release must be the same
Conflicts: kubernetes-master < %{version}-%{release}
Conflicts: kubernetes-master > %{version}-%{release}

%description node
Kubernetes services for node host

%package client
Summary: Kubernetes client tools

BuildRequires: golang >= 1.2-7

%description client
Kubernetes client tools like kubectl

%prep
%setup -q -n %{k8s_repo}-%{k8s_commit} -T -b 1
# Hack test-cmd.sh to be run with os binaries
%patch9 -p1
# Keep solid port for kube-proxy
%patch10 -p1

%setup -q -n %{con_repo}-%{con_commit} -T -b 2
%setup -q -n %{repo}-%{commit}

# copy contrib folder to origin
cp -r ../%{k8s_repo}-%{k8s_commit}/contrib/completions/bash/kubectl contrib/completions/bash/.
# copy contrib folder to origin
cp -r ../%{con_repo}-%{con_commit}/init contrib/.
# copy docs/admin and docs/man to origin
cp -r ../%{k8s_repo}-%{k8s_commit}/docs/admin docs/admin
cp -r ../%{k8s_repo}-%{k8s_commit}/docs/man docs/man
# copy cmd/kube-version change to origin
cp -r ../%{k8s_repo}-%{k8s_commit}/cmd/kube-version-change cmd/.
rm -rf cmd/kube-version-change/import_known_versions.go

%patch2 -p1

# internal -> inteernal
%patch4 -p1
%patch5 -p1
# do not unset default cluster
%patch7 -p1

# add missing -s for --server
%patch8 -p1

%build
# Don't judge me for this ... it's so bad.
mkdir _build

# Horrid hack because golang loves to just bundle everything
pushd _build
    mkdir -p src/github.com/openshift
    ln -s $(dirs +1 -l) src/%{openshift_ip}
popd

# Gaming the GOPATH to include the third party bundled libs at build
# time. This is bad and I feel bad.
mkdir _thirdpartyhacks
pushd _thirdpartyhacks
    ln -s \
        $(dirs +1 -l)/Godeps/_workspace/src/ \
            src
popd
export GOPATH=$(pwd)/_build:$(pwd)/_thirdpartyhacks:%{buildroot}%{gopath}:%{gopath}

%{!?ldflags:
%global ldflags -X github.com/openshift/origin/pkg/version.majorFromGit %{O4N_GIT_MAJOR_VERSION} -X github.com/openshift/origin/pkg/version.minorFromGit %{O4N_GIT_MINOR_VERSION} -X github.com/openshift/origin/pkg/version.versionFromGit %{O4N_GIT_VERSION} -X github.com/openshift/origin/pkg/version.commitFromGit %{shortcommit} -X k8s.io/kubernetes/pkg/version.gitCommit %{k8s_shortcommit} -X k8s.io/kubernetes/pkg/version.gitVersion %{K8S_GIT_VERSION}
}

go install -ldflags "%{ldflags}" %{openshift_ip}/cmd/openshift

export GOPATH=$(pwd)/Godeps/_workspace:$(pwd)/_build:%{buildroot}%{gopath}:%{gopath}
go install -ldflags "%{ldflags}" %{openshift_ip}/cmd/kube-version-change

# convert md to man
pushd docs
pushd admin
cp kube-apiserver.md kube-controller-manager.md kube-proxy.md kube-scheduler.md kubelet.md ..
popd
cp %{SOURCE33} genmanpages.sh
bash genmanpages.sh
popd

%install

install -d %{buildroot}%{_bindir}

echo "+++ INSTALLING ${bin}"
install -p -m 755 _build/bin/openshift %{buildroot}%{_bindir}/openshift
# kube-apiserver can not be symlink when %%attr is used
install -p -m 755 _build/bin/openshift %{buildroot}%{_bindir}/kube-apiserver

for cmd in kubectl kubelet kube-proxy kube-controller-manager kube-scheduler; do
    ln -s %{_bindir}/openshift %{buildroot}%{_bindir}/$cmd
done

# TODO: kube-version-change missing
install -p -m 755 _build/bin/kube-version-change %{buildroot}%{_bindir}/kube-version-change


# k8s has its own contrib as well (for kubectl completion)

# install the bash completion
install -d -m 0755 %{buildroot}%{_datadir}/bash-completion/completions/
install -t %{buildroot}%{_datadir}/bash-completion/completions/ contrib/completions/bash/kubectl

# !!!!Adding contrib directory to tarball

# install config files
install -d -m 0755 %{buildroot}%{_sysconfdir}/%{name}
install -m 644 -t %{buildroot}%{_sysconfdir}/%{name} contrib/init/systemd/environ/*

# install service files
install -d -m 0755 %{buildroot}%{_unitdir}
install -m 0644 -t %{buildroot}%{_unitdir} contrib/init/systemd/*.service

# install manpages
install -d %{buildroot}%{_mandir}/man1
install -p -m 644 docs/man/man1/* %{buildroot}%{_mandir}/man1
# from k8s tarball copied docs/man/man1/*.1

# install the place the kubelet defaults to put volumes
install -d %{buildroot}%{_sharedstatedir}/kubelet

# place contrib/init/systemd/tmpfiles.d/kubernetes.conf to /usr/lib/tmpfiles.d/kubernetes.conf
install -d -m 0755 %{buildroot}%{_tmpfilesdir}
install -p -m 0644 -t %{buildroot}/%{_tmpfilesdir} contrib/init/systemd/tmpfiles.d/kubernetes.conf

# place files for unit-test rpm
install -d -m 0755 %{buildroot}%{_sharedstatedir}/kubernetes-unit-test/
pushd ../%{k8s_repo}-%{k8s_commit}
# only files for hack/test-cmd.sh atm
for d in docs examples hack; do
  cp -a $d %{buildroot}%{_sharedstatedir}/kubernetes-unit-test/
done
popd

%pre master
getent group kube >/dev/null || groupadd -r kube
getent passwd kube >/dev/null || useradd -r -g kube -d / -s /sbin/nologin \
        -c "Kubernetes user" kube

%post master
%systemd_post kube-apiserver kube-scheduler kube-controller-manager

%preun master
%systemd_preun kube-apiserver kube-scheduler kube-controller-manager

%postun master
%systemd_postun

%pre node
getent group kube >/dev/null || groupadd -r kube
getent passwd kube >/dev/null || useradd -r -g kube -d / -s /sbin/nologin \
        -c "Kubernetes user" kube

%post node
%systemd_post kubelet kube-proxy

%preun node
%systemd_preun kubelet kube-proxy

%postun node
%systemd_postun

#define license tag if not already defined
%{!?_licensedir:%global license %doc}

%files
# empty as it depends on master and node

%files master
%license LICENSE
%doc *.md
%{_mandir}/man1/kube-apiserver.1*
%{_mandir}/man1/kube-controller-manager.1*
%{_mandir}/man1/kube-scheduler.1*
%{_bindir}/openshift
%attr(754, -, kube) %caps(cap_net_bind_service=ep) %{_bindir}/kube-apiserver
%{_bindir}/kube-controller-manager
%{_bindir}/kube-scheduler
%{_bindir}/kube-version-change
%{_unitdir}/kube-apiserver.service
%{_unitdir}/kube-controller-manager.service
%{_unitdir}/kube-scheduler.service
%dir %{_sysconfdir}/%{name}
%config(noreplace) %{_sysconfdir}/%{name}/apiserver
%config(noreplace) %{_sysconfdir}/%{name}/scheduler
%config(noreplace) %{_sysconfdir}/%{name}/config
%config(noreplace) %{_sysconfdir}/%{name}/controller-manager
%{_tmpfilesdir}/kubernetes.conf

%files node
%license LICENSE
%doc *.md
%{_mandir}/man1/kubelet.1*
%{_mandir}/man1/kube-proxy.1*
%{_bindir}/openshift
%{_bindir}/kubelet
%{_bindir}/kube-proxy
%{_bindir}/kube-version-change
%{_unitdir}/kube-proxy.service
%{_unitdir}/kubelet.service
%dir %{_sharedstatedir}/kubelet
%dir %{_sysconfdir}/%{name}
%config(noreplace) %{_sysconfdir}/%{name}/config
%config(noreplace) %{_sysconfdir}/%{name}/kubelet
%config(noreplace) %{_sysconfdir}/%{name}/proxy
%{_tmpfilesdir}/kubernetes.conf

%files client
%license LICENSE
%doc *.md
%{_mandir}/man1/kubectl.1*
%{_mandir}/man1/kubectl-*
%{_bindir}/openshift
%{_bindir}/kubectl
%{_datadir}/bash-completion/completions/kubectl

%files unit-test
%{_sharedstatedir}/kubernetes-unit-test/

%changelog
* Fri Nov 20 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.3.origin.git4c8e6f4
- Bump to upstream a41c9ff38d52fd508481c3c2bac13d52871fde02

* Fri Nov 20 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.2.origin.git4c8e6f4
- Update to origin v1.1

* Fri Nov 20 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.1.origin.git4c8e6f4
- Update to origin v1.0.8
