# Version 1.1.0 #

## SigimaX Version 1.1.0 ##

### PlotPy adapters ###

* PlotPy annotations created or edited through SigimaX are now stored with
  Sigima's renderer-independent annotation model, so they may be displayed by
  other supported visualization backends without carrying PlotPy-specific
  serialization data.
* Existing PlotPy annotations remain readable without modifying the source
  object. Supported annotations are migrated when an edit is accepted, while
  malformed, unknown, or partially supported payloads are preserved unchanged.
* Canonical annotation identifiers, metadata, extensions, and persistent lock
  state are preserved across PlotPy editing round trips. Application-specific
  opaque annotation entries continue to coexist with graphical annotations.

### Requirements ###

* Sigima 1.3.0 or later is required for the portable annotation model and
  PlotPy conversion helpers.