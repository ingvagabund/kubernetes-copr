# https://bugzilla.redhat.com/show_bug.cgi?id=995136#c12
%global _dwz_low_mem_die_limit 0
%global provider	github
%global provider_tld	com
%global project		kubernetes
%global repo		kubernetes
# https://github.com/kubernetes/kubernetes
%global provider_prefix	%{provider}.%{provider_tld}/%{project}/%{repo}
%global import_path     k8s.io/kubernetes
%global commit		6234d6a0abd3323cd08c52602e4a91e47fc9491c
%global shortcommit	%(c=%{commit}; echo ${c:0:7})

#I really need this, otherwise "version_ldflags=$(kube::version_ldflags)"
# does not work
%global _buildshell	/bin/bash
%global _checkshell	/bin/bash

Name:		kubernetes
Version:	1.0.7
Release:	0.1.git%{shortcommit}%{?dist}
Summary:        Container cluster management
License:        ASL 2.0
URL:            %{import_path}
Source0:        https://%{provider_prefix}/archive/%{commit}/%{repo}-%{shortcommit}.tar.gz
Source2:        genmanpages.sh

Patch1:         Fix-Persistent-Volumes-and-Persistent-Volume-Claims.patch
Patch2:         Change-etcd-server-port.patch
Patch3:         build-with-debug-info.patch
Patch4:         change-internal-to-inteernal.patch
Patch5:         Update-github.com-elazarl-go-bindata-assetfs-to-at-l.patch
# backport refactoring of TLS connection, upstream issue #15224
Patch6:         backport-refactoring-of-TLS-connection.patch

# It obsoletes cadvisor but needs its source code (literally integrated)
Obsoletes:      cadvisor

ExclusiveArch:  x86_64

# kubernetes is decomposed into master and node subpackages
# require both of them for updates
Requires: kubernetes-master = %{version}-%{release}
Requires: kubernetes-node = %{version}-%{release}

%description
%{summary}

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
%setup -q -n %{repo}-%{commit}
%patch1 -p1
%patch2 -p1
%patch3 -p1
%patch4 -p1
%patch5 -p1

# backport refactoring of TLS connection
%patch6 -p1

%build
export KUBE_GIT_TREE_STATE="clean"
export KUBE_GIT_COMMIT=%{commit}
export KUBE_GIT_VERSION=v1.0.6

hack/build-go.sh --use_go_build
hack/build-go.sh --use_go_build cmd/kube-version-change

# convert md to man
pushd docs
pushd admin
cp kube-apiserver.md kube-controller-manager.md kube-proxy.md kube-scheduler.md kubelet.md ..
popd
cp %{SOURCE2} genmanpages.sh
bash genmanpages.sh
popd

%install
. hack/lib/init.sh
kube::golang::setup_env

output_path="${KUBE_OUTPUT_BINPATH}/$(kube::golang::current_platform)"

binaries=(kube-apiserver kube-controller-manager kube-scheduler kube-proxy kubelet kubectl kube-version-change)
install -m 755 -d %{buildroot}%{_bindir}
for bin in "${binaries[@]}"; do
  echo "+++ INSTALLING ${bin}"
  install -p -m 755 -t %{buildroot}%{_bindir} ${output_path}/${bin}
done

# install the bash completion
install -d -m 0755 %{buildroot}%{_datadir}/bash-completion/completions/
install -t %{buildroot}%{_datadir}/bash-completion/completions/ contrib/completions/bash/kubectl

# install config files
install -d -m 0755 %{buildroot}%{_sysconfdir}/%{name}
install -m 644 -t %{buildroot}%{_sysconfdir}/%{name} contrib/init/systemd/environ/*

# install service files
install -d -m 0755 %{buildroot}%{_unitdir}
install -m 0644 -t %{buildroot}%{_unitdir} contrib/init/systemd/*.service

# install manpages
install -d %{buildroot}%{_mandir}/man1
install -p -m 644 docs/man/man1/* %{buildroot}%{_mandir}/man1

# install the place the kubelet defaults to put volumes
install -d %{buildroot}%{_sharedstatedir}/kubelet

# place contrib/init/systemd/tmpfiles.d/kubernetes.conf to /usr/lib/tmpfiles.d/kubernetes.conf
install -d -m 0755 %{buildroot}%{_tmpfilesdir}
install -p -m 0644 -t %{buildroot}/%{_tmpfilesdir} contrib/init/systemd/tmpfiles.d/kubernetes.conf

# remove porter as it is built inside docker container without options for debug info
rm -rf contrib/for-tests/porter

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

%files
# empty as it depends on master and node

%files master
%doc README.md LICENSE CONTRIB.md CONTRIBUTING.md DESIGN.md
%{_mandir}/man1/kube-apiserver.1*
%{_mandir}/man1/kube-controller-manager.1*
%{_mandir}/man1/kube-scheduler.1*
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
%doc README.md LICENSE CONTRIB.md CONTRIBUTING.md DESIGN.md
%{_mandir}/man1/kubelet.1*
%{_mandir}/man1/kube-proxy.1*
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
%doc README.md LICENSE CONTRIB.md CONTRIBUTING.md DESIGN.md
%{_mandir}/man1/kubectl.1*
%{_mandir}/man1/kubectl-*
%{_bindir}/kubectl
%{_datadir}/bash-completion/completions/kubectl

%if 0%{?with_devel}
%files devel
%doc README.md LICENSE CONTRIB.md CONTRIBUTING.md DESIGN.md
%dir %{gopath}/src/k8s.io
%{gopath}/src/%{import_path}
%endif


%changelog
* Mon Nov 09 2015 jchaloup <jchaloup@redhat.com> - 1.0.7-0.1.git6234d6a
- Update to v1.0.7
  related: #1274854

