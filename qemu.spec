# build-time settings that support --with or --without:
#
# = kvmonly =
# Build only KVM-enabled QEMU targets, on KVM-enabled architectures.
#
# Disabled by default.
#
ExclusiveArch: ppc64
#
# Disabled by default, except on RHEL.  Only makes sense with kvmonly.
#
# = rbd =
# Enable rbd support.
#
# Enable by default, except on RHEL.
#
# = separate_kvm =
# Do not build and install stuff that would colide with separately packaged KVM.
#
# Disabled by default, except on EPEL.

%define mcp 8

%if 0%{?rhel}
# RHEL-specific defaults:
%bcond_without kvmonly          # enabled
%bcond_without exclusive_x86_64 # enabled
%bcond_with    rbd              # disabled
%bcond_without spice            # enabled
%bcond_without seccomp          # enabled
%bcond_with    xfsprogs         # disabled
%bcond_with    separate_kvm     # disabled - for EPEL
%else
# General defaults:
%bcond_with    kvmonly          # disabled
%bcond_with    exclusive_x86_64 # disabled
%bcond_without rbd              # enabled
%bcond_without spice            # enabled
%bcond_without seccomp          # enabled
%bcond_without xfsprogs         # enabled
%bcond_with    separate_kvm     # disabled
%endif

%global SLOF_gittagdate 20140514

%if %{without separate_kvm}
%global kvm_archs %{ix86} x86_64 ppc64 s390x
%else
%global kvm_archs %{ix86} ppc64 s390x
%endif
%if %{with exclusive_x86_64}
%global kvm_archs x86_64
%endif


%global have_usbredir 1

%ifarch %{ix86} x86_64
%if %{with seccomp}
%global have_seccomp 1
%endif
%if %{with spice}
%global have_spice   1
%endif
%else
%if 0%{?rhel}
%global have_usbredir 0
%endif
%endif

%global need_qemu_kvm %{with kvmonly}
%global need_kvm_modfile 0

# LTC: overrides
%if 0%{?mcp}
%bcond_with    xfsprogs         # disabled
%ifarch s390x
%global have_usbredir 0
%endif # end s390x
%endif

# These values for system_xyz are overridden below for non-kvmonly builds.
# Instead, these values for kvm_package are overridden below for kvmonly builds.
# Somewhat confusing, but avoids complicated nested conditionals.

%ifarch %{ix86}
%global system_x86    kvm
%global kvm_package   system-x86
%global kvm_target    i386
%global need_qemu_kvm 1
%endif
%ifarch x86_64
%global system_x86    kvm
%global kvm_package   system-x86
%global kvm_target    x86_64
%global need_qemu_kvm 1
%endif
%ifarch ppc64
%global system_ppc    kvm
%global kvm_package   system-ppc
%global kvm_target    ppc64
%global need_kvm_modfile 1
%global need_qemu_kvm 1
%endif
%ifarch s390x
%global system_s390x  kvm
%global kvm_package   system-s390x
%global kvm_target    s390x
%global need_kvm_modfile 1
%endif

%if %{with kvmonly}
# If kvmonly, put the qemu-kvm binary in the qemu-kvm package
%global kvm_package   kvm
%else


# If not kvmonly, build all packages and give them normal names. qemu-kvm
# is a simple wrapper package and is only build for archs that support KVM.
%global user          user
%global system_alpha  system-alpha
%global system_arm    system-arm
%global system_cris   system-cris
%global system_lm32   system-lm32
%global system_m68k   system-m68k
%global system_microblaze   system-microblaze
%global system_mips   system-mips
%global system_or32   system-or32
%global system_ppc    system-ppc
%global system_s390x  system-s390x
%global system_sh4    system-sh4
%global system_sparc  system-sparc
%global system_x86    system-x86
%global system_xtensa   system-xtensa
%global system_unicore32   system-unicore32
%endif

%undefine user
%undefine system_alpha
%undefine system_arm
%undefine system_cris
%undefine system_lm32
%undefine system_m68k
%undefine system_microblaze
%undefine system_mips
%undefine system_or32
%undefine system_sh4
%undefine system_sparc
%undefine system_xtensa
%undefine system_unicore32
%undefine system_s390x

# libfdt is only needed to build ARM, Microblaze or PPC emulators
%if 0%{?system_arm:1}%{?system_microblaze:1}%{?system_ppc:1}
%global need_fdt      1
%endif

Summary: QEMU is a FAST! processor emulator
Name: qemu
Version: 1.6.0
%define release .0
%define frobisher_release .12
Release: 2%{?dist}%{frobisher_release}%{?release}
# Epoch: because we pushed a qemu-1.0 package. AIUI this can't ever be dropped
Epoch: 2
License: GPLv2+ and LGPLv2+ and BSD
Group: Development/Tools
URL: http://www.qemu.org/
# RHEL will build Qemu only on x86_64:
%if %{with kvmonly}
ExclusiveArch: %{kvm_archs}
%endif

# OOM killer breaks builds with parallel make on s390(x)
%ifarch s390 s390x
%define _smp_mflags %{nil}
%endif

#requite git for pulling soure from git repo
BuildRequires: git
BuildRequires: SDL-devel
BuildRequires: zlib-devel
BuildRequires: which
%{!?mcp:BuildRequires: texi2html}
BuildRequires: gnutls-devel
BuildRequires: cyrus-sasl-devel
BuildRequires: libtool
BuildRequires: libaio-devel
BuildRequires: rsync
BuildRequires: pciutils-devel
BuildRequires: pulseaudio-libs-devel
BuildRequires: libiscsi-devel
BuildRequires: ncurses-devel
BuildRequires: libattr-devel
%if 0%{?have_usbredir}
BuildRequires: usbredir-devel >= 0.5.2
%endif
%{?!mcp:BuildRequires: texinfo}
# for /usr/bin/pod2man
%if 0%{?fedora} > 18
BuildRequires: perl-podlators
%endif
%if 0%{?have_spice:1}
BuildRequires: spice-protocol >= 0.12.2
BuildRequires: spice-server-devel >= 0.12.0
%endif
%if 0%{?have_seccomp:1}
BuildRequires: libseccomp-devel >= 1.0.0
%endif
# For network block driver
BuildRequires: libcurl-devel
%if %{with rbd}
# For rbd block driver
BuildRequires: ceph-devel
%endif
# We need both because the 'stap' binary is probed for by configure
BuildRequires: systemtap
BuildRequires: systemtap-sdt-devel
# For smartcard NSS support
BuildRequires: nss-devel
# For XFS discard support in raw-posix.c
%if %{with xfsprogs}
#BuildRequires: xfsprogs-devel
%endif
# For VNC JPEG support
BuildRequires: libjpeg-devel
# For VNC PNG support
BuildRequires: libpng-devel
# For uuid generation
BuildRequires: libuuid-devel
# For BlueZ device support
BuildRequires: bluez-libs-devel
# For Braille device support
BuildRequires: brlapi-devel
%if 0%{?need_fdt:1}
# For FDT device tree support
BuildRequires: libfdt-devel
%endif
# For test suite
BuildRequires: check-devel
# For virtfs
BuildRequires: libcap-devel
# Hard requirement for version >= 1.3
BuildRequires: pixman-devel
%if 0%{?fedora} > 18
# For gluster support
BuildRequires: glusterfs-devel >= 3.4.0
BuildRequires: glusterfs-api-devel >= 3.4.0
%endif

%if 0%{?user:1}
Requires: %{name}-%{user} = %{epoch}:%{version}-%{release}
%endif
%if 0%{?system_alpha:1}
Requires: %{name}-%{system_alpha} = %{epoch}:%{version}-%{release}
%endif
%if 0%{?system_arm:1}
Requires: %{name}-%{system_arm} = %{epoch}:%{version}-%{release}
%endif
%if 0%{?system_cris:1}
Requires: %{name}-%{system_cris} = %{epoch}:%{version}-%{release}
%endif
%if 0%{?system_lm32:1}
Requires: %{name}-%{system_lm32} = %{epoch}:%{version}-%{release}
%endif
%if 0%{?system_m68k:1}
Requires: %{name}-%{system_m68k} = %{epoch}:%{version}-%{release}
%endif
%if 0%{?system_microblaze:1}
Requires: %{name}-%{system_microblaze} = %{epoch}:%{version}-%{release}
%endif
%if 0%{?system_mips:1}
Requires: %{name}-%{system_mips} = %{epoch}:%{version}-%{release}
%endif
%if 0%{?system_or32:1}
Requires: %{name}-%{system_or32} = %{epoch}:%{version}-%{release}
%endif
%if 0%{?system_ppc:1}
Requires: %{name}-%{system_ppc} = %{epoch}:%{version}-%{release}
%endif
%if 0%{?system_s390x:1}
Requires: %{name}-%{system_s390x} = %{epoch}:%{version}-%{release}
%endif
%if 0%{?system_sh4:1}
Requires: %{name}-%{system_sh4} = %{epoch}:%{version}-%{release}
%endif
%if 0%{?system_sparc:1}
Requires: %{name}-%{system_sparc} = %{epoch}:%{version}-%{release}
%endif
%if 0%{?system_unicore32:1}
Requires: %{name}-%{system_unicore32} = %{epoch}:%{version}-%{release}
%endif
%if 0%{?system_x86:1}
Requires: %{name}-%{system_x86} = %{epoch}:%{version}-%{release}
%endif
%if 0%{?system_xtensa:1}
Requires: %{name}-%{system_xtensa} = %{epoch}:%{version}-%{release}
%endif
%if %{without separate_kvm}
Requires: %{name}-img = %{epoch}:%{version}-%{release}
%else
Requires: %{name}-img
%endif

%define qemudocdir %{_docdir}/%{name}

%description
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation. QEMU has two operating modes:

 * Full system emulation. In this mode, QEMU emulates a full system (for
   example a PC), including a processor and various peripherials. It can be
   used to launch different Operating Systems without rebooting the PC or
   to debug system code.
 * User mode emulation. In this mode, QEMU can launch Linux processes compiled
   for one CPU on another CPU.

As QEMU requires no host kernel patches to run, it is safe and easy to use.

%if %{without kvmonly}
%ifarch %{kvm_archs}
%package kvm
Summary: QEMU metapackage for KVM support
Group: Development/Tools
Requires: qemu-%{kvm_package} = %{epoch}:%{version}-%{release}

%description kvm
This is a meta-package that provides a qemu-system-<arch> package for native
architectures where kvm can be enabled. For example, in an x86 system, this
will install qemu-system-x86
%endif
%endif

%package  img
Summary: QEMU command line tool for manipulating disk images
Group: Development/Tools

%description img
This package provides a command line tool for manipulating disk images

%package  common
Summary: QEMU common files needed by all QEMU targets
Group: Development/Tools
Requires(post): /usr/bin/getent
Requires(post): /usr/sbin/groupadd
Requires(post): /usr/sbin/useradd
Requires(post): systemd-units
Requires(preun): systemd-units
Requires(postun): systemd-units
%description common
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation.

This package provides the common files needed by all QEMU targets

%package guest-agent
Summary: QEMU guest agent
Group: System Environment/Daemons
Requires(post): systemd-units
Requires(preun): systemd-units
Requires(postun): systemd-units

%description guest-agent
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation.

This package provides an agent to run inside guests, which communicates
with the host over a virtio-serial channel named "org.qemu.guest_agent.0"

This package does not need to be installed on the host OS.

%post guest-agent
%systemd_post qemu-guest-agent.service

%preun guest-agent
%systemd_preun qemu-guest-agent.service

%postun guest-agent
%systemd_postun_with_restart qemu-guest-agent.service


%package -n ksm
Summary: Kernel Samepage Merging services
Group: Development/Tools
Requires: %{name}-common = %{epoch}:%{version}-%{release}
Requires(post): systemd-units
Requires(postun): systemd-units
%description -n ksm
Kernel Samepage Merging (KSM) is a memory-saving de-duplication feature,
that merges anonymous (private) pages (not pagecache ones).

This package provides service files for disabling and tuning KSM.


%if 0%{?user:1}
%package %{user}
Summary: QEMU user mode emulation of qemu targets
Group: Development/Tools
Requires: %{name}-common = %{epoch}:%{version}-%{release}
Requires(post): systemd-units
Requires(postun): systemd-units
%description %{user}
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation.

This package provides the user mode emulation of qemu targets
%endif

%if 0%{?system_x86:1}
%package %{system_x86}
Summary: QEMU system emulator for x86
Group: Development/Tools
Requires: %{name}-common = %{epoch}:%{version}-%{release}
Provides: kvm = 85
Obsoletes: kvm < 85
Requires: seavgabios-bin
Requires: seabios-bin >= 0.6.0-2
Requires: sgabios-bin
Requires: ipxe-roms-qemu
%if 0%{?have_seccomp:1}
Requires: libseccomp >= 1.0.0
%endif

%description %{system_x86}
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation.

This package provides the system emulator for x86. When being run in a x86
machine that supports it, this package also provides the KVM virtualization
platform.
%endif

%if 0%{?system_alpha:1}
%package %{system_alpha}
Summary: QEMU system emulator for Alpha
Group: Development/Tools
Requires: %{name}-common = %{epoch}:%{version}-%{release}
%description %{system_alpha}
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation.

This package provides the system emulator for Alpha systems.
%endif

%if 0%{?system_arm:1}
%package %{system_arm}
Summary: QEMU system emulator for ARM
Group: Development/Tools
Requires: %{name}-common = %{epoch}:%{version}-%{release}
%description %{system_arm}
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation.

This package provides the system emulator for ARM boards.
%endif

%if 0%{?system_mips:1}
%package %{system_mips}
Summary: QEMU system emulator for MIPS
Group: Development/Tools
Requires: %{name}-common = %{epoch}:%{version}-%{release}
%description %{system_mips}
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation.

This package provides the system emulator for MIPS boards.
%endif

%if 0%{?system_cris:1}
%package %{system_cris}
Summary: QEMU system emulator for CRIS
Group: Development/Tools
Requires: %{name}-common = %{epoch}:%{version}-%{release}
%description %{system_cris}
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation.

This package provides the system emulator for CRIS boards.
%endif

%if 0%{?system_lm32:1}
%package %{system_lm32}
Summary: QEMU system emulator for LatticeMico32
Group: Development/Tools
Requires: %{name}-common = %{epoch}:%{version}-%{release}
%description %{system_lm32}
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation.

This package provides the system emulator for LatticeMico32 boards.
%endif

%if 0%{?system_m68k:1}
%package %{system_m68k}
Summary: QEMU system emulator for ColdFire (m68k)
Group: Development/Tools
Requires: %{name}-common = %{epoch}:%{version}-%{release}
%description %{system_m68k}
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation.

This package provides the system emulator for ColdFire boards.
%endif

%if 0%{?system_microblaze:1}
%package %{system_microblaze}
Summary: QEMU system emulator for Microblaze
Group: Development/Tools
Requires: %{name}-common = %{epoch}:%{version}-%{release}
%description %{system_microblaze}
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation.

This package provides the system emulator for Microblaze boards.
%endif

%if 0%{?system_or32:1}
%package %{system_or32}
Summary: QEMU system emulator for OpenRisc32
Group: Development/Tools
Requires: %{name}-common = %{epoch}:%{version}-%{release}
%description %{system_or32}
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation.

This package provides the system emulator for OpenRisc32 boards.
%endif

%if 0%{?system_s390x:1}
%package %{system_s390x}
Summary: QEMU system emulator for S390
Group: Development/Tools
Requires: %{name}-common = %{epoch}:%{version}-%{release}
%description %{system_s390x}
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation.

This package provides the system emulator for S390 systems.
%endif

%if 0%{?system_sh4:1}
%package %{system_sh4}
Summary: QEMU system emulator for SH4
Group: Development/Tools
Requires: %{name}-common = %{epoch}:%{version}-%{release}
%description %{system_sh4}
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation.

This package provides the system emulator for SH4 boards.
%endif

%if 0%{?system_sparc:1}
%package %{system_sparc}
Summary: QEMU system emulator for SPARC
Group: Development/Tools
Requires: %{name}-common = %{epoch}:%{version}-%{release}
Requires: openbios
%description %{system_sparc}
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation.

This package provides the system emulator for SPARC and SPARC64 systems.
%endif

%if 0%{?system_ppc:1}
%package %{system_ppc}
Summary: QEMU system emulator for PPC
Group: Development/Tools
Requires: %{name}-common = %{epoch}:%{version}-%{release}
Requires: openbios
Requires: SLOF = 0.1.git%{SLOF_gittagdate}
%description %{system_ppc}
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation.

This package provides the system emulator for PPC and PPC64 systems.
%endif

%if 0%{?system_xtensa:1}
%package %{system_xtensa}
Summary: QEMU system emulator for Xtensa
Group: Development/Tools
Requires: %{name}-common = %{epoch}:%{version}-%{release}
%description %{system_xtensa}
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation.

This package provides the system emulator for Xtensa boards.
%endif

%if 0%{?system_unicore32:1}
%package %{system_unicore32}
Summary: QEMU system emulator for Unicore32
Group: Development/Tools
Requires: %{name}-common = %{epoch}:%{version}-%{release}
%description %{system_unicore32}
QEMU is a generic and open source processor emulator which achieves a good
emulation speed by using dynamic translation.

This package provides the system emulator for Unicore32 boards.
%endif

%ifarch %{kvm_archs}
%package kvm-tools
Summary: KVM debugging and diagnostics tools
Group: Development/Tools

%description kvm-tools
This package contains some diagnostics and debugging tools for KVM,
such as kvm_stat.
%endif

%if %{without separate_kvm}
%package -n libcacard
Summary:        Common Access Card (CAC) Emulation
Group:          Development/Libraries

%description -n libcacard
Common Access Card (CAC) emulation library.

%package -n libcacard-tools
Summary:        CAC Emulation tools
Group:          Development/Libraries
Requires:       libcacard = %{epoch}:%{version}-%{release}

%description -n libcacard-tools
CAC emulation tools.

%package -n libcacard-devel
Summary:        CAC Emulation devel
Group:          Development/Libraries
Requires:       libcacard = %{epoch}:%{version}-%{release}

%description -n libcacard-devel
CAC emulation development files.
%endif

%debug_package

%prep
%if 0%{mcp}
    echo %{mcp}
%endif
git clone  git://9.3.189.26/frobisher/qemu.git ./
git checkout --track remotes/origin/powerkvm

%build
%if %{with kvmonly}
    buildarch="%{kvm_target}-softmmu"
%else
    buildarch="x86_64-softmmu i386-softmmu ppc64-softmmu"
%endif

# --build-id option is used for giving info to the debug packages.
extraldflags="-Wl,--build-id";
buildldflags="VL_LDFLAGS=-Wl,--build-id"

%ifarch s390
# drop -g flag to prevent memory exhaustion by linker
%global optflags %(echo %{optflags} | sed 's/-g//')
sed -i.debug 's/"-g $CFLAGS"/"$CFLAGS"/g' configure
%endif


dobuild() {
    ./configure \
        --prefix=%{_prefix} \
        --libdir=%{_libdir} \
        --sysconfdir=%{_sysconfdir} \
        --interp-prefix=%{_prefix}/qemu-%%M \
        --audio-drv-list=pa,sdl,alsa,oss \
        --localstatedir=%{_localstatedir} \
        --libexecdir=%{_libexecdir} \
        --disable-strip \
        --extra-ldflags="$extraldflags -pie -Wl,-z,relro -Wl,-z,now" \
        --extra-cflags="%{optflags} -fPIE -DPIE" \
        --enable-mixemu \
        --enable-trace-backend=dtrace \
        --disable-werror \
        --disable-xen \
        --enable-kvm \
        --enable-curl\
%if 0%{?have_spice:1}
        --enable-spice \
%endif
%if %{without rbd}
        --disable-rbd \
%endif
        "$@"
#%if 0%{?need_fdt:1}
#        --enable-fdt \
#%else
#        --disable-fdt \
#%endif
    echo "config-host.mak contents:"
    echo "==="
    cat config-host.mak
    echo "==="

    make V=1 %{?_smp_mflags} $buildldflags
}

dobuild --target-list="$buildarch"

gcc ksmctl.c -O2 -g -o ksmctl


%install

%define _udevdir /lib/udev/rules.d

install -D -p -m 0744 ksm.service 	$RPM_BUILD_ROOT/lib/systemd/system/ksm.service
install -D -p -m 0644 ksm.sysconfig $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig/ksm
install -D -p -m 0755 ksmctl $RPM_BUILD_ROOT/lib/systemd/ksmctl

install -D -p -m 0744 ksmtuned.service 	$RPM_BUILD_ROOT/lib/systemd/system/ksmtuned.service
install -D -p -m 0755 ksmtuned 	$RPM_BUILD_ROOT%{_sbindir}/ksmtuned
install -D -p -m 0644 ksmtuned.conf $RPM_BUILD_ROOT%{_sysconfdir}/ksmtuned.conf

%ifarch %{kvm_archs}
%if 0%{?need_kvm_modfile}
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig/modules
install -m 0755 kvm.modules $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig/modules/kvm.modules
%else
# LTC: keep mcpsource consistent for intel arches
touch -a kvm.modules
%endif

mkdir -p $RPM_BUILD_ROOT%{_bindir}/
mkdir -p $RPM_BUILD_ROOT%{_udevdir}

install -m 0755 scripts/kvm/kvm_stat $RPM_BUILD_ROOT%{_bindir}/
install -m 0644 80-kvm.rules $RPM_BUILD_ROOT%{_udevdir}
%endif

make DESTDIR=$RPM_BUILD_ROOT install

%if 0%{?need_qemu_kvm}
%ifarch ppc64
install -m 0755 qemu-kvm-ppc64.sh $RPM_BUILD_ROOT%{_bindir}/qemu-kvm
%else
install -m 0755 qemu-kvm.sh $RPM_BUILD_ROOT%{_bindir}/qemu-kvm
%endif
%else
# LTC: keep mcpsource consistent for non-intel arches
touch -a qemu-kvm.sh
%endif

%if %{with kvmonly}
rm $RPM_BUILD_ROOT%{_bindir}/qemu-system-%{kvm_target}
rm $RPM_BUILD_ROOT%{_datadir}/systemtap/tapset/qemu-system-%{kvm_target}.stp
%endif

%if ! 0%{?mcp}
chmod -x ${RPM_BUILD_ROOT}%{_mandir}/man1/*
install -D -p -m 0644 -t ${RPM_BUILD_ROOT}%{qemudocdir} Changelog README TODO COPYING COPYING.LIB LICENSE
for emu in $RPM_BUILD_ROOT%{_bindir}/qemu-system-*; do
    ln -sf qemu.1.gz $RPM_BUILD_ROOT%{_mandir}/man1/$(basename $emu).1.gz
done
%if 0%{?need_qemu_kvm}
ln -sf qemu.1.gz $RPM_BUILD_ROOT%{_mandir}/man1/qemu-kvm.1.gz
%endif
%endif # end not mcp

install -D -p -m 0644 qemu.sasl $RPM_BUILD_ROOT%{_sysconfdir}/sasl2/qemu.conf

# Provided by package openbios
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/openbios-ppc
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/openbios-sparc32
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/openbios-sparc64
# Provided by package SLOF
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/slof.bin

# Remove possibly unpackaged files.  Unlike others that are removed
# unconditionally, these firmware files are still distributed as a binary
# together with the qemu package.  We should try to move at least s390-zipl.rom
# to a separate package...  Discussed here on the packaging list:
# https://lists.fedoraproject.org/pipermail/packaging/2012-July/008563.html
%if 0%{!?system_alpha:1}
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/palcode-clipper
%endif
%if 0%{!?system_microblaze:1}
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/petalogix*.dtb
%endif
%if 0%{!?system_ppc:1}
rm -f ${RPM_BUILD_ROOT}%{_datadir}/%{name}/bamboo.dtb
rm -f ${RPM_BUILD_ROOT}%{_datadir}/%{name}/ppc_rom.bin
rm -f ${RPM_BUILD_ROOT}%{_datadir}/%{name}/spapr-rtas.bin
%endif
%if 0%{!?system_s390x:1}
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/s390-zipl.rom
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/s390-ccw.img
%endif
%if 0%{!?system_x86:1}
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/efi-e1000.rom
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/efi-eepro100.rom
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/efi-ne2k_pci.rom
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/efi-pcnet.rom
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/efi-rtl8139.rom
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/efi-virtio.rom
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/target-x86_64.conf
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/acpi-dsdt.aml
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/kvmvapic.bin
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/linuxboot.bin
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/multiboot.bin
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/q35-acpi-dsdt.aml
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/qemu-icon.bmp
rm -rf ${RPM_BUILD_ROOT}%{_sysconfdir}/%{name}/target-x86_64.conf
%endif

# Provided by package ipxe
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/pxe*rom
# Provided by package seavgabios
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/vgabios*bin
# Provided by package seabios
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/bios.bin
# Provided by package sgabios
rm -rf ${RPM_BUILD_ROOT}%{_datadir}/%{name}/sgabios.bin

%if 0%{?system_x86:1}
# the pxe gpxe images will be symlinks to the images on
# /usr/share/ipxe, as QEMU doesn't know how to look
# for other paths, yet.
pxe_link() {
  ln -s ../ipxe/$2.rom %{buildroot}%{_datadir}/%{name}/pxe-$1.rom
}

pxe_link e1000 8086100e
pxe_link ne2k_pci 10ec8029
pxe_link pcnet 10222000
pxe_link rtl8139 10ec8139
pxe_link virtio 1af41000

rom_link() {
    ln -s $1 %{buildroot}%{_datadir}/%{name}/$2
}

rom_link ../seavgabios/vgabios-isavga.bin vgabios.bin
rom_link ../seavgabios/vgabios-cirrus.bin vgabios-cirrus.bin
rom_link ../seavgabios/vgabios-qxl.bin vgabios-qxl.bin
rom_link ../seavgabios/vgabios-stdvga.bin vgabios-stdvga.bin
rom_link ../seavgabios/vgabios-vmware.bin vgabios-vmware.bin
rom_link ../seabios/bios.bin bios.bin
rom_link ../sgabios/sgabios.bin sgabios.bin
%endif

%if 0%{?user:1}
mkdir -p $RPM_BUILD_ROOT%{_exec_prefix}/lib/binfmt.d
for i in dummy \
%ifnarch %{ix86} x86_64
    qemu-i386 \
%endif
%ifnarch alpha
    qemu-alpha \
%endif
%ifnarch %{arm}
    qemu-arm \
%endif
    qemu-armeb \
    qemu-cris \
    qemu-microblaze qemu-microblazeel \
%ifnarch mips
    qemu-mips qemu-mips64 \
%endif
%ifnarch mipsel
    qemu-mipsel qemu-mips64el \
%endif
%ifnarch m68k
    qemu-m68k \
%endif
%ifnarch ppc ppc64
    qemu-ppc qemu-ppc64abi32 qemu-ppc64 \
%endif
%ifnarch sparc sparc64
    qemu-sparc qemu-sparc32plus qemu-sparc64 \
%endif
%ifnarch s390 s390x
    qemu-s390x \
%endif
%ifnarch sh4
    qemu-sh4 \
%endif
    qemu-sh4eb \
; do
  test $i = dummy && continue
  grep /$i:\$ qemu.binfmt > $RPM_BUILD_ROOT%{_exec_prefix}/lib/binfmt.d/$i.conf
  chmod 644 $RPM_BUILD_ROOT%{_exec_prefix}/lib/binfmt.d/$i.conf
done < qemu.binfmt
%endif

# For the qemu-guest-agent subpackage install the systemd
# service and udev rules.
mkdir -p $RPM_BUILD_ROOT%{_unitdir}
mkdir -p $RPM_BUILD_ROOT%{_udevdir}
install -m 0644 qemu-guest-agent.service $RPM_BUILD_ROOT%{_unitdir}
install -m 0644 99-qemu-guest-agent.rules $RPM_BUILD_ROOT%{_udevdir}

# Install rules to use the bridge helper with libvirt's virbr0
install -m 0644 bridge.conf $RPM_BUILD_ROOT%{_sysconfdir}/qemu
chmod u+s $RPM_BUILD_ROOT%{_libexecdir}/qemu-bridge-helper

find $RPM_BUILD_ROOT -name '*.la' -or -name '*.a' | xargs rm -f
find $RPM_BUILD_ROOT -name "libcacard.so*" -exec chmod +x \{\} \;

%if %{with separate_kvm}
rm -f $RPM_BUILD_ROOT%{_bindir}/qemu-kvm
rm -f $RPM_BUILD_ROOT%{_bindir}/qemu-img
rm -f $RPM_BUILD_ROOT%{_bindir}/qemu-io
rm -f $RPM_BUILD_ROOT%{_bindir}/qemu-nbd
rm -f $RPM_BUILD_ROOT%{_mandir}/man1/qemu-img.1*
rm -f $RPM_BUILD_ROOT%{_mandir}/man8/qemu-nbd.8*

rm -f $RPM_BUILD_ROOT%{_sbindir}/ksmtuned
rm -f $RPM_BUILD_ROOT%{_sysconfdir}/ksmtuned.conf
rm -f $RPM_BUILD_ROOT%{_sysconfdir}/sysconfig/ksm
rm -f $RPM_BUILD_ROOT/lib/systemd/ksmctl
rm -f $RPM_BUILD_ROOT/lib/systemd/system/ksm.service
rm -f $RPM_BUILD_ROOT/lib/systemd/system/ksmtuned.service

rm -f $RPM_BUILD_ROOT%{_bindir}/qemu-ga
rm -f $RPM_BUILD_ROOT%{_unitdir}/qemu-guest-agent.service
rm -f $RPM_BUILD_ROOT%{_udevdir}/99-qemu-guest-agent.rules

rm -f $RPM_BUILD_ROOT%{_bindir}/vscclient
rm -f $RPM_BUILD_ROOT%{_libdir}/libcacard*
rm -f $RPM_BUILD_ROOT%{_libdir}/pkgconfig/libcacard.pc
rm -rf $RPM_BUILD_ROOT%{_includedir}/cacard
%endif

%check
make check

%ifarch %{kvm_archs}
%post %{kvm_package}
# load kvm modules now, so we can make sure no reboot is needed.
# If there's already a kvm module installed, we don't mess with it
sh %{_sysconfdir}/sysconfig/modules/kvm.modules &> /dev/null || :
udevadm trigger --subsystem-match=misc --sysname-match=kvm --action=add || :
%endif

%if %{without separate_kvm}
%post common
getent group kvm >/dev/null || groupadd -g 36 -r kvm
getent group qemu >/dev/null || groupadd -g 107 -r qemu
getent passwd qemu >/dev/null || \
  useradd -r -u 107 -g qemu -G kvm -d / -s /sbin/nologin \
    -c "qemu user" qemu

%post -n ksm
%systemd_post ksm.service
%systemd_post ksmtuned.service
%preun -n ksm
%systemd_preun ksm.service
%systemd_preun ksmtuned.service
%postun -n ksm
%systemd_postun_with_restart ksm.service
%systemd_postun_with_restart ksmtuned.service
%endif

%if 0%{?user:1}
%post %{user}
/bin/systemctl --system try-restart systemd-binfmt.service &>/dev/null || :

%postun %{user}
/bin/systemctl --system try-restart systemd-binfmt.service &>/dev/null || :
%endif

%global kvm_files \
%if 0%{?need_kvm_modfile} \
%{_sysconfdir}/sysconfig/modules/kvm.modules \
%endif \
%{_udevdir}/80-kvm.rules

%if 0%{?need_qemu_kvm}
%global qemu_kvm_files \
%{_bindir}/qemu-kvm \
%endif

%files
%defattr(-,root,root)

%ifarch %{kvm_archs}
%files kvm
%defattr(-,root,root)
%endif

%files common
%defattr(-,root,root)
%if ! 0%{?mcp}
%dir %{qemudocdir}
%doc %{qemudocdir}/Changelog
%doc %{qemudocdir}/README
%doc %{qemudocdir}/TODO
%doc %{qemudocdir}/qemu-doc.html
%doc %{qemudocdir}/qemu-tech.html
%doc %{qemudocdir}/qmp-commands.txt
%doc %{qemudocdir}/COPYING
%doc %{qemudocdir}/COPYING.LIB
%doc %{qemudocdir}/LICENSE
%endif # end not mcp
%dir %{_datadir}/%{name}/
%{_datadir}/%{name}/qemu_logo_no_text.svg
%{_datadir}/%{name}/keymaps/
#%{_mandir}/man1/qemu.1*
#%{_mandir}/man1/virtfs-proxy-helper.1*
%{_bindir}/virtfs-proxy-helper
%{_libexecdir}/qemu-bridge-helper
%config(noreplace) %{_sysconfdir}/sasl2/qemu.conf
%dir %{_sysconfdir}/qemu
%config(noreplace) %{_sysconfdir}/qemu/bridge.conf

%if %{without separate_kvm}
%files -n ksm
/lib/systemd/system/ksm.service
/lib/systemd/ksmctl
%config(noreplace) %{_sysconfdir}/sysconfig/ksm
/lib/systemd/system/ksmtuned.service
%{_sbindir}/ksmtuned
%config(noreplace) %{_sysconfdir}/ksmtuned.conf
%endif

%if %{without separate_kvm}
%files guest-agent
%defattr(-,root,root,-)
%doc COPYING README
%{_bindir}/qemu-ga
%{_unitdir}/qemu-guest-agent.service
%{_udevdir}/99-qemu-guest-agent.rules
%endif

%if 0%{?user:1}
%files %{user}
%defattr(-,root,root)
%{_exec_prefix}/lib/binfmt.d/qemu-*.conf
%{_bindir}/qemu-i386
%{_bindir}/qemu-x86_64
%{_bindir}/qemu-alpha
%{_bindir}/qemu-arm
%{_bindir}/qemu-armeb
%{_bindir}/qemu-cris
%{_bindir}/qemu-m68k
%{_bindir}/qemu-microblaze
%{_bindir}/qemu-microblazeel
%{_bindir}/qemu-mips
%{_bindir}/qemu-mipsel
%{_bindir}/qemu-or32
%{_bindir}/qemu-ppc
%{_bindir}/qemu-ppc64
%{_bindir}/qemu-ppc64abi32
%{_bindir}/qemu-s390x
%{_bindir}/qemu-sh4
%{_bindir}/qemu-sh4eb
%{_bindir}/qemu-sparc
%{_bindir}/qemu-sparc32plus
%{_bindir}/qemu-sparc64
%{_bindir}/qemu-unicore32
%{_datadir}/systemtap/tapset/qemu-i386.stp
%{_datadir}/systemtap/tapset/qemu-x86_64.stp
%{_datadir}/systemtap/tapset/qemu-alpha.stp
%{_datadir}/systemtap/tapset/qemu-arm.stp
%{_datadir}/systemtap/tapset/qemu-armeb.stp
%{_datadir}/systemtap/tapset/qemu-cris.stp
%{_datadir}/systemtap/tapset/qemu-m68k.stp
%{_datadir}/systemtap/tapset/qemu-microblaze.stp
%{_datadir}/systemtap/tapset/qemu-microblazeel.stp
%{_datadir}/systemtap/tapset/qemu-mips.stp
%{_datadir}/systemtap/tapset/qemu-mipsel.stp
%{_datadir}/systemtap/tapset/qemu-or32.stp
%{_datadir}/systemtap/tapset/qemu-ppc.stp
%{_datadir}/systemtap/tapset/qemu-ppc64.stp
%{_datadir}/systemtap/tapset/qemu-ppc64abi32.stp
%{_datadir}/systemtap/tapset/qemu-s390x.stp
%{_datadir}/systemtap/tapset/qemu-sh4.stp
%{_datadir}/systemtap/tapset/qemu-sh4eb.stp
%{_datadir}/systemtap/tapset/qemu-sparc.stp
%{_datadir}/systemtap/tapset/qemu-sparc32plus.stp
%{_datadir}/systemtap/tapset/qemu-sparc64.stp
%{_datadir}/systemtap/tapset/qemu-unicore32.stp
%endif

%if 0%{?system_x86:1}
%files %{system_x86}
%defattr(-,root,root)
%if %{without kvmonly}
%{_bindir}/qemu-system-x86_64
%{_bindir}/qemu-system-i386
%{_datadir}/systemtap/tapset/qemu-system-x86_64.stp
%{_datadir}/systemtap/tapset/qemu-system-i386.stp
%endif
%{_datadir}/%{name}/acpi-dsdt.aml
%{_datadir}/%{name}/q35-acpi-dsdt.aml
%{_datadir}/%{name}/bios.bin
%{_datadir}/%{name}/sgabios.bin
%{_datadir}/%{name}/linuxboot.bin
%{_datadir}/%{name}/multiboot.bin
%{_datadir}/%{name}/kvmvapic.bin
%{_datadir}/%{name}/vgabios.bin
%{_datadir}/%{name}/vgabios-cirrus.bin
%{_datadir}/%{name}/vgabios-qxl.bin
%{_datadir}/%{name}/vgabios-stdvga.bin
%{_datadir}/%{name}/vgabios-vmware.bin
%{_datadir}/%{name}/pxe-e1000.rom
%{_datadir}/%{name}/pxe-virtio.rom
%{_datadir}/%{name}/pxe-pcnet.rom
%{_datadir}/%{name}/pxe-rtl8139.rom
%{_datadir}/%{name}/pxe-ne2k_pci.rom
%{_datadir}/%{name}/qemu-icon.bmp
%{_datadir}/%{name}/efi*

%config(noreplace) %{_sysconfdir}/qemu/target-x86_64.conf
%if %{without separate_kvm}
%ifarch %{ix86} x86_64
%{?kvm_files:}
%{?qemu_kvm_files:}
%endif
%endif
%endif

%ifarch %{kvm_archs}
%files kvm-tools
%defattr(-,root,root,-)
%{_bindir}/kvm_stat
%endif

%if 0%{?system_alpha:1}
%files %{system_alpha}
%defattr(-,root,root)
%{_bindir}/qemu-system-alpha
%{_datadir}/systemtap/tapset/qemu-system-alpha.stp
%{_datadir}/%{name}/palcode-clipper
%endif

%if 0%{?system_arm:1}
%files %{system_arm}
%defattr(-,root,root)
%{_bindir}/qemu-system-arm
%{_datadir}/systemtap/tapset/qemu-system-arm.stp
%endif

%if 0%{?system_mips:1}
%files %{system_mips}
%defattr(-,root,root)
%{_bindir}/qemu-system-mips
%{_bindir}/qemu-system-mipsel
%{_bindir}/qemu-system-mips64
%{_bindir}/qemu-system-mips64el
%{_datadir}/systemtap/tapset/qemu-system-mips.stp
%{_datadir}/systemtap/tapset/qemu-system-mipsel.stp
%{_datadir}/systemtap/tapset/qemu-system-mips64el.stp
%{_datadir}/systemtap/tapset/qemu-system-mips64.stp
%endif

%if 0%{?system_cris:1}
%files %{system_cris}
%defattr(-,root,root)
%{_bindir}/qemu-system-cris
%{_datadir}/systemtap/tapset/qemu-system-cris.stp
%endif

%if 0%{?system_lm32:1}
%files %{system_lm32}
%defattr(-,root,root)
%{_bindir}/qemu-system-lm32
%{_datadir}/systemtap/tapset/qemu-system-lm32.stp
%endif

%if 0%{?system_m68k:1}
%files %{system_m68k}
%defattr(-,root,root)
%{_bindir}/qemu-system-m68k
%{_datadir}/systemtap/tapset/qemu-system-m68k.stp
%endif

%if 0%{?system_microblaze:1}
%files %{system_microblaze}
%defattr(-,root,root)
%{_bindir}/qemu-system-microblaze
%{_bindir}/qemu-system-microblazeel
%{_datadir}/systemtap/tapset/qemu-system-microblaze.stp
%{_datadir}/systemtap/tapset/qemu-system-microblazeel.stp
%{_datadir}/%{name}/petalogix*.dtb
%endif

%if 0%{?system_or32:1}
%files %{system_or32}
%defattr(-,root,root)
%{_bindir}/qemu-system-or32
%{_datadir}/systemtap/tapset/qemu-system-or32.stp
%endif

%if 0%{?system_s390x:1}
%files %{system_s390x}
%defattr(-,root,root)
%{_bindir}/qemu-system-s390x
%{_datadir}/systemtap/tapset/qemu-system-s390x.stp
%{_datadir}/%{name}/s390*
%ifarch s390x
%{?kvm_files:}
%{?qemu_kvm_files:}
%endif
%endif

%if 0%{?system_sh4:1}
%files %{system_sh4}
%defattr(-,root,root)
%{_bindir}/qemu-system-sh4
%{_bindir}/qemu-system-sh4eb
%{_datadir}/systemtap/tapset/qemu-system-sh4.stp
%{_datadir}/systemtap/tapset/qemu-system-sh4eb.stp
%endif

%if 0%{?system_sparc:1}
%files %{system_sparc}
%defattr(-,root,root)
%{_bindir}/qemu-system-sparc
%{_bindir}/qemu-system-sparc64
%{_datadir}/systemtap/tapset/qemu-system-sparc.stp
%{_datadir}/systemtap/tapset/qemu-system-sparc64.stp
%endif

%if 0%{?system_ppc:1}
%files %{system_ppc}
%defattr(-,root,root)
%if %{without kvmonly}
%{_bindir}/qemu-system-ppc64
%{_bindir}/qemu-system-i386
%{_bindir}/qemu-system-x86_64
%{_datadir}/systemtap/tapset/qemu-system-ppc64.stp
%{_datadir}/systemtap/tapset/qemu-system-i386.stp
%{_datadir}/systemtap/tapset/qemu-system-x86_64.stp
%endif
%{_datadir}/%{name}/bamboo.dtb
%{_datadir}/%{name}/ppc_rom.bin
%{_datadir}/%{name}/spapr-rtas.bin
%ifarch ppc64
%{?kvm_files:}
%{?qemu_kvm_files:}
%endif
%endif

%if 0%{?system_unicore32:1}
%files %{system_unicore32}
%defattr(-,root,root)
%{_bindir}/qemu-system-unicore32
%{_datadir}/systemtap/tapset/qemu-system-unicore32.stp
%endif

%if 0%{?system_xtensa:1}
%files %{system_xtensa}
%defattr(-,root,root)
%{_bindir}/qemu-system-xtensa
%{_bindir}/qemu-system-xtensaeb
%{_datadir}/systemtap/tapset/qemu-system-xtensa.stp
%{_datadir}/systemtap/tapset/qemu-system-xtensaeb.stp
%endif

%if %{without separate_kvm}
%files img
%defattr(-,root,root)
%{_bindir}/qemu-img
%{_bindir}/qemu-io
%{_bindir}/qemu-nbd

%files -n libcacard
%defattr(-,root,root,-)
%{_libdir}/libcacard.so.*

%files -n libcacard-tools
%defattr(-,root,root,-)
%{_bindir}/vscclient

%files -n libcacard-devel
%defattr(-,root,root,-)
%{_includedir}/cacard
%{_libdir}/libcacard.so
%{_libdir}/pkgconfig/libcacard.pc
%endif

%changelog
* Fri Feb 21 2014 Li Yong Qiao <qiaoly@cn.ibm.com> 1.6.0-2.10.1
- Beta2:
  -- Flush queue whenever can_receive can go from false to true(Fix BZ 103621).
  -- Fix a regression introduced in pbeta1 by 65a930

* Thu Feb 13 2014 Li Yong Qiao <qiaoly@cn.ibm.com>
- Beta1 update 1:
  -- Fixes for migration issues.
* Tue Feb 4 2014 Crístian Viana <vianac@linux.vnet.ibm.com> 1.6.0-2.10.0
- Beta1:
  -- bootindex: fix compile warning
  -- memory: fix 128 arithmetic in info mtree
  -- PPC: KVM: store SLB slot number
  -- kvm.modules: always load kvm and kvm-pr
  -- spapr_pci: fix unplug for boot-time devices
  -- Bump SPEC file to pbeta1
* Tue Jan 14 2014 Wang Sen<wangsen@linux.vnet.ibm.com> 1.6.0-2.7
- Build7 update1:
  -- Add --enable-curl to configure.
  -- PPC: KVM: suppress warnings about not supported SPRs
  -- change the type of addr from uint32_t to hwaddr
* Tue Jan 07 2014 Wang Sen<wangsen@linux.vnet.ibm.com> 1.6.0-2.7
- Build7:
  -- Fix bug 100523: spapr: fix client-architecture-support for SMP config
  -- spapr: fix device nodes handling for bootindex
  -- 29 update patches:
  	-- 1. latest VFIO from upstream, kernel changes are required, posted separately
  	-- 2. "-device ...,bootindex=X" support 
  	-- 3. SPR fixes for KVM - now they are
  really put/set
* Tue Dec 10 2013 Wang Sen<wangsen@linux.vnet.ibm.com> 1.6.0-2.6
- Build6:
  -- Merge patch: spapr_pci: hotplug, fix unplug race conditions
  -- Build qemu-system-x86_64 package back.
  -- Bump SLOF git date to 20131209
* Fri Dec 6 2013 Qiao Li Yong<qiaoly@cn.ibm.com> 1.6.0-2.5
- Build5 update2:
  Since we support now 2 different types of KVM, and there are 2 more kernel modules for that, load them in kvm.modules script.
  LTC bug 100523, This fixes a compatibility mode selection for POWER7(architected).
  Moves "-cpu" options parsing from vl.c (which only compilesfor ppc64-softmmu) to qom/cpu.c (which compiles for both ppc64-softmmuand ppc64-linux-user).
* Tue Nov 26 2013 Wang Sen<wangsen@linux.vnet.ibm.com> 1.6.0-2.5
- Build5 update1: spapr: fix "mare sure RMA is in the first node"
* Thu Nov 21 2013 Wang Sen<wangsen@linux.vnet.ibm.com> 1.6.0-1
- Update spec file for pbuild5:
  Enable SPAPR PCI Hotplug Support.
  Drop qemu-system-x86_64 and qemu-system-s390x.
  Drop SOURCES files because we start to track them in the git repo.
  Bump SLOF git tag to 20131118.
  Reset release to 0, bump frobisher_release to 5.
  Change the prefix of release from 1 to 2.
* Fri Nov 08 2013 Wang Sen<wangsen@linux.vnet.ibm.com> 1.6.0-1
- Build4 update3: fix double define and assignment of cap_spapr_multitce
* Fri Nov 08 2013 Wang Sen<wangsen@linux.vnet.ibm.com> 1.6.0-1
- Build4 update2: fix cpu_dt_id to support ibm, client-architecture-support 
* Fri Nov 08 2013 Wang Sen<wangsen@linux.vnet.ibm.com> 1.6.0-1
- Build4 update1: Include 3 bug fix patch from Alexey.
--'990bc3a2': ppc: fix ppc32 compile error
--'df1ffcd4': spapr: make sure RMA is in first mode of first memory node
--'f1b2244f': ppc: introduce CPUPPCState::cpu_dt_id
* Tue Oct 29 2013 Wang Sen<wangsen@linux.vnet.ibm.com> 1.6.0-1
- Build packages for KoP build4.
* Thu Oct 17 2013 wangsen@linux.vnet.ibm.com 1.6.0-1
- Build debuginfo package.
* Thu Oct 17 2013 wangsen@linux.vnet.ibm.com 1.6.0-1
- clean up the comments
* Mon Aug 26 2013 qiaoly@cn.ibm.com
- upgrade version to 1.6.0-1.mcp8_0.2.ppc64
* Thu Jul 11 2013 baseuser@ibm.com
- Base-8.x spec file
