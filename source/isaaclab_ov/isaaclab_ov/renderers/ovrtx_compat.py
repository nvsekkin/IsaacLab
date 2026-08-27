# Copyright (c) 2022-2026, The Isaac Lab Project Developers (https://github.com/isaac-sim/IsaacLab/blob/main/CONTRIBUTORS.md).
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Version compatibility between OVRTX, OVStage, and Isaac Lab.

OVRTX 0.4 keys ``frame.render_vars`` by render-var source name (``"LdrColor"``), while
0.5 keys it by the authored RenderVar prim path (``"/Render/Vars/LdrColor"``). The
installed version cannot change while the process runs, so the key form is resolved once
at import and published as :data:`RENDER_VAR_FRAME_KEYS`; per-frame code indexes that
mapping instead of re-checking the version.

OVRTX and OVStage also expose a native ABI boundary that package metadata does not constrain.
The supported pair is checked before renderer construction so an incompatible install fails with
an actionable Python exception instead of aborting in native OVStage population.

The public extras stay pinned to ``ovrtx==0.4.1.364340``; a missing or unparsable install
keeps the 0.4 key form.
"""

from __future__ import annotations

import importlib.metadata
import logging
from collections.abc import Mapping
from types import MappingProxyType

from packaging.version import InvalidVersion, Version

from .ovrtx_usd import render_var_prim_paths_by_source

logger = logging.getLogger(__name__)

# First OVRTX version that keys ``frame.render_vars`` by RenderVar prim path.
_PRIM_PATH_RENDER_VARS_VERSION = Version("0.5")
_OVRTX_04_MIN_VERSION = Version("0.4")
_OVRTX_05_MIN_VERSION = Version("0.5")
_OVRTX_06_MIN_VERSION = Version("0.6")
_OVSTAGE_01_MIN_VERSION = Version("0.1.1.355824")
_OVSTAGE_02_MIN_VERSION = Version("0.2.0.370625")
_OVSTAGE_03_MIN_VERSION = Version("0.3")


def detect_ovrtx_version() -> Version | None:
    """Return the installed ``ovrtx`` version.

    Read from distribution metadata rather than ``ovrtx.__version__`` so it does not
    require importing the runtime. An unparsable version is logged and reported as
    missing, which keeps the OVRTX 0.4 behavior.

    Returns:
        The installed version, or ``None`` when ``ovrtx`` is absent or its version string
        cannot be parsed.
    """
    try:
        raw = importlib.metadata.version("ovrtx")
    except importlib.metadata.PackageNotFoundError:
        return None
    try:
        return Version(raw)
    except InvalidVersion:
        logger.warning("Could not parse ovrtx version %r; assuming the OVRTX 0.4 render-var API.", raw)
        return None


def detect_ovstage_version() -> Version | None:
    """Return the installed ``ovstage`` version.

    Returns:
        The installed version, or ``None`` when ``ovstage`` is absent or its version string
        cannot be parsed.
    """
    try:
        raw = importlib.metadata.version("ovstage")
    except importlib.metadata.PackageNotFoundError:
        return None
    try:
        return Version(raw)
    except InvalidVersion:
        logger.warning("Could not parse ovstage version %r.", raw)
        return None


def validate_ovrtx_ovstage_compatibility(
    ovrtx_version: Version | None,
    ovstage_version: Version | None,
) -> None:
    """Validate the native OVRTX and OVStage package pairing.

    Args:
        ovrtx_version: Installed OVRTX version, or ``None`` when it cannot be resolved.
        ovstage_version: Installed OVStage version, or ``None`` when it cannot be resolved.

    Raises:
        RuntimeError: If a known OVRTX release line is paired with an unsupported OVStage version.
    """
    required_ovstage: str | None = None
    is_compatible = True
    if ovrtx_version is not None and _OVRTX_04_MIN_VERSION <= ovrtx_version < _OVRTX_05_MIN_VERSION:
        required_ovstage = ">=0.1.1.355824,<0.2"
        is_compatible = (
            ovstage_version is not None and _OVSTAGE_01_MIN_VERSION <= ovstage_version < _OVSTAGE_02_MIN_VERSION
        )
    elif ovrtx_version is not None and _OVRTX_05_MIN_VERSION <= ovrtx_version < _OVRTX_06_MIN_VERSION:
        required_ovstage = ">=0.2.0.370625,<0.3"
        is_compatible = (
            ovstage_version is not None and _OVSTAGE_02_MIN_VERSION <= ovstage_version < _OVSTAGE_03_MIN_VERSION
        )

    if required_ovstage is not None and not is_compatible:
        installed_ovstage = str(ovstage_version) if ovstage_version is not None else "missing or unparsable"
        raise RuntimeError(
            "Unsupported OVRTX/OVStage package combination: "
            f"ovrtx {ovrtx_version} requires ovstage{required_ovstage}, but found {installed_ovstage}. "
            "Install a compatible pair before creating OVRTXRenderer."
        )


def validate_installed_ovrtx_ovstage() -> None:
    """Validate the installed OVRTX and OVStage distributions."""
    validate_ovrtx_ovstage_compatibility(OVRTX_VERSION, OVSTAGE_VERSION)


def uses_prim_path_render_vars(version: Version | None) -> bool:
    """Return whether ``version`` keys ``frame.render_vars`` by RenderVar prim path.

    Args:
        version: OVRTX version to classify, or ``None`` when OVRTX is unavailable.

    Returns:
        Whether ``version`` is OVRTX 0.5 or newer.
    """
    return version is not None and version >= _PRIM_PATH_RENDER_VARS_VERSION


def build_render_var_frame_keys(version: Version | None) -> Mapping[str, str]:
    """Return the ``frame.render_vars`` key for every render-var source under ``version``.

    Args:
        version: OVRTX version the keys are built for, or ``None`` when OVRTX is unavailable.

    Returns:
        Read-only mapping of render-var source name to frame key: the source name itself on
        OVRTX 0.4, or the authored RenderVar prim path on OVRTX 0.5 and later.
    """
    prim_paths = render_var_prim_paths_by_source()
    if uses_prim_path_render_vars(version):
        return MappingProxyType(dict(prim_paths))
    return MappingProxyType({source: source for source in prim_paths})


OVRTX_VERSION: Version | None = detect_ovrtx_version()
"""Installed OVRTX version, or ``None`` when it is unavailable or unparsable."""

OVSTAGE_VERSION: Version | None = detect_ovstage_version()
"""Installed OVStage version, or ``None`` when it is unavailable or unparsable."""

RENDER_VAR_FRAME_KEYS: Mapping[str, str] = build_render_var_frame_keys(OVRTX_VERSION)
"""Maps render-var source name to its ``frame.render_vars`` key for the installed OVRTX."""
