# KHIPU Model Package — `.khipu` v0.1

Status: **SOFTWARE_REFERENCE / PACKAGE_VERIFIED_ONLY**

A `.khipu` file is a deterministic, bounded ZIP container with canonical
`manifest.json`, one canonical graph, and optional weights/tokenizer/config
artifacts. Verification occurs without extracting files.

Required protections:

- POSIX-relative canonical paths only;
- no `..`, absolute paths, backslashes, NULs, symlinks, encryption or directory entries;
- duplicate and case-colliding names rejected;
- bounded entry count, individual size, total size and compression ratio;
- exact archive file set must equal the manifest file set;
- SHA-256 and byte-size verification for every payload;
- canonical UTF-8 JSON manifest;
- semantic parsing and digest verification of the entry graph;
- known KIDS opcode names only.

A verified package proves container integrity under its commitments. It does not
prove model quality, license compliance, safe behavior, hardware execution or
real-world outcomes. Rev v0.1 hard-locks `hardware_execution=UNAVAILABLE` and
`production_eligible=false`.
