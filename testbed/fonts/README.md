# Local font fixtures

This directory is a local-only fixture source for Elementor fidelity tests.

Copy the exact font files needed by the current design into this directory. Font binaries are ignored by Git and are not part of Morpher source control.

For the Discovery font proof, place:

- `Butler.woff2`
- `HKGrotesk-Regular.woff2`

Docker Compose bind-mounts this directory read-only into WordPress at:

`/var/www/html/wp-content/morpher-test-fonts`

With the testbed running on `http://localhost:8080`, the files are available at:

- `http://localhost:8080/wp-content/morpher-test-fonts/Butler.woff2`
- `http://localhost:8080/wp-content/morpher-test-fonts/HKGrotesk-Regular.woff2`

This is only a testbed hook. It does not make font delivery part of the Morpher compiler or Elementor renderer.
