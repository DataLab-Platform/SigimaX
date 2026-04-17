# Copyright (c) DataLab Platform Developers, BSD 3-Clause license, see LICENSE file.

"""
Configuration System
====================

This example demonstrates SigimaX's configuration system — typed option fields
with ``get()``/``set()``/``context()`` API, JSON persistence, and validation.

The configuration system is the backbone of any SigimaX-based application.
It provides:

- **Type safety**: Options are validated on set
- **Context managers**: Temporary overrides that auto-restore
- **Serialization**: JSON round-trip for persistence
- **Enum constraints**: Options restricted to specific choices
"""

# %%
# Importing necessary modules
# ---------------------------

from sigima.config import TypedOptionField

from sigimax.config import EnumOptionField, SigimaXOptions

# %%
# Creating a custom configuration
# --------------------------------
#
# Subclass :class:`~sigimax.config.SigimaXOptions` and add typed fields.


class DemoOptions(SigimaXOptions):
    """Demo configuration with various option types."""

    ENV_VAR = "DEMO_OPTIONS_JSON"

    def __init__(self):
        super().__init__()
        self.app_name.set("ConfigDemo", sync_env=False)

        self.iterations = TypedOptionField(
            self,
            "iterations",
            default=100,
            expected_type=int,
            description="Number of iterations",
        )
        self.precision = TypedOptionField(
            self,
            "precision",
            default=1e-6,
            expected_type=float,
            description="Convergence precision",
        )
        self.algorithm = EnumOptionField(
            self,
            "algorithm",
            default="gradient",
            choices=["gradient", "newton", "simplex"],
            description="Optimization algorithm",
        )
        self.verbose = TypedOptionField(
            self,
            "verbose_mode",
            default=False,
            expected_type=bool,
            description="Enable verbose logging",
        )

        # Capture defaults for reset support
        self._defaults.update(
            {
                name: getattr(self, name).get(sync_env=False)
                for name in ("iterations", "precision", "algorithm", "verbose")
            }
        )


# %%
# Basic get/set operations
# -------------------------

conf = DemoOptions()

print("=== Basic get/set ===")
print(f"Iterations: {conf.iterations.get()}")
print(f"Algorithm:  {conf.algorithm.get()}")

conf.iterations.set(500)
conf.algorithm.set("newton")
print(f"Updated iterations: {conf.iterations.get()}")
print(f"Updated algorithm:  {conf.algorithm.get()}")

# %%
# Context manager for temporary overrides
# -----------------------------------------
#
# The ``context()`` method temporarily overrides an option and automatically
# restores the previous value when leaving the block.

print("\n=== Context manager ===")
print(f"Before context: iterations = {conf.iterations.get()}")

with conf.iterations.context(10):
    print(f"Inside context: iterations = {conf.iterations.get()}")

print(f"After context:  iterations = {conf.iterations.get()}")

# %%
# Enum validation
# ----------------
#
# ``EnumOptionField`` rejects values not in the allowed choices.

print("\n=== Enum validation ===")
try:
    conf.algorithm.set("invalid_algorithm")
    print("ERROR: Should have raised ValueError")
except ValueError as e:
    print(f"Correctly rejected invalid value: {e}")

# %%
# Serialization round-trip
# -------------------------
#
# Options can be serialized to a dictionary (and from there to JSON).

print("\n=== Serialization ===")
d = conf.to_dict()
print(f"Serialized keys: {sorted(d.keys())[:8]}...")

# Create a fresh config and restore from dict
conf2 = DemoOptions()
conf2.from_dict(d)
print(f"Restored iterations: {conf2.iterations.get()}")
print(f"Restored algorithm:  {conf2.algorithm.get()}")

# %%
# Reset to defaults
# ------------------

print("\n=== Reset to defaults ===")
conf.iterations.set(999)
print(f"Before reset: {conf.iterations.get()}")
conf.reset_to_defaults()
print(f"After reset:  {conf.iterations.get()}")

# %%
# Listing all options
# --------------------
#
# ``list_options()`` returns the names of all registered option fields.

print("\n=== All options ===")
for name in sorted(conf.list_options()):
    print(f"  {name}")

# %%
# Summary
# -------
#
# SigimaX's configuration system provides:
#
# - **Typed fields**: ``TypedOptionField`` for int/float/str/bool,
#   ``EnumOptionField`` for constrained choices
# - **Context managers**: ``option.context(value)`` for scoped overrides
# - **Serialization**: ``to_dict()`` / ``from_dict()`` for JSON persistence
# - **Validation**: Type checking and enum constraint enforcement
# - **Reset**: ``reset_to_defaults()`` to restore initial values
