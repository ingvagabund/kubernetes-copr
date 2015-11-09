# https://bugzilla.redhat.com/show_bug.cgi?id=995136#c12
%global _dwz_low_mem_die_limit 0
%global provider	github
%global provider_tld	com
%global project		kubernetes
%global repo		kubernetes
# https://github.com/kubernetes/kubernetes
%global provider_prefix	%{provider}.%{provider_tld}/%{project}/%{repo}
%global import_path     k8s.io/kubernetes
%global commit		7d6c8b640f2e90cf2347fb46ef4cf46cd3280015
%global shortcommit	%(c=%{commit}; echo ${c:0:7})

%global con_provider         github
%global con_provider_tld     com  
%global con_project          kubernetes
%global con_repo             contrib
%global con_provider_prefix  %{con_provider}.%{con_provider_tld}/%{con_project}/%{con_repo}
%global con_commit           36816275fd53c7a2ef59650c80e2820fe3595584
%global con_shortcommit      %(c=%{con_commit}; echo ${c:0:7})

#I really need this, otherwise "version_ldflags=$(kube::version_ldflags)"
# does not work
%global _buildshell	/bin/bash
%global _checkshell	/bin/bash

Name:		kubernetes
Version:	1.1.0
Release:	0.1.git%{shortcommit}%{?dist}
Summary:        Container cluster management
License:        ASL 2.0
URL:            %{import_path}
Source0:        https://%{provider_prefix}/archive/%{commit}/%{repo}-%{shortcommit}.tar.gz
Source1:        https://%{con_provider_prefix}/archive/%{con_commit}/%{con_repo}-%{con_shortcommit}.tar.gz
Source2:        genmanpages.sh

Patch2:         Change-etcd-server-port.patch
Patch3:         build-with-debug-info.patch
Patch4:         change-internal-to-inteernal.patch

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
%setup -q -n %{con_repo}-%{con_commit} -T -b 1
%setup -q -n %{repo}-%{commit}
# move content of contrib back to kubernetes
mv ../%{con_repo}-%{con_commit}/init contrib/init

%patch2 -p1
%patch3 -p1
%patch4 -p1

%build
export KUBE_GIT_TREE_STATE="clean"
export KUBE_GIT_COMMIT=%{commit}
export KUBE_GIT_VERSION=v1.0.6

hack/build-go.sh --use_go_build
# remove import_known_versions.go
rm -rf cmd/kube-version-change/import_known_versions.go
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
* Mon Nov 09 2015 jchaloup <jchaloup@redhat.com> - 1.1.0-0.1.git7d6c8b6
- Update to v1.1.0
  related: #1274854

* Mon Nov 09 2015 jchaloup <jchaloup@redhat.com> - 1.0.7-0.1.git6234d6a
- Update to v1.0.7
  related: #1274854

