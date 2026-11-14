# Existing bounded descriptor read: early rejection

After safe descriptor traversal, require regular file as before; if fstat size exceeds
caller-supplied limit, raise existing ReadBudgetExceeded without body read. During reads,
retain limit+1 sentinel and reject overflow before accumulating/joining the excess.
This is conservative if a local file shrinks after stat; no false safety claim that stat
proves immutable bytes. Later recorded digest checks remain required. All descriptors close
on refusal/error. Growth after stat must still fail. Existing limits/HTTP mapping unchanged:
intake8MiB, archive16MiB; legacy sys.maxsize remains no practical cap. No permission changes
or lock release; not an aggregate memory budget or concurrent admission implementation.
