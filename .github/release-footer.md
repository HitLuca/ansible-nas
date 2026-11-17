## Upgrading

Read the sections above before upgrading, and back up `docker_home` first: application migrations are forward-only, so checking out the previous version does not roll a container back. Roles that are new in a release are disabled until you set their `<role>_enabled` flag in your inventory.

## Testing

Every application role has a molecule scenario that converges the role, proves idempotence, verifies the container is running, then disables the role and asserts the container is gone. CI runs the scenarios of the roles a pull request touches, and the full matrix weekly to catch images that disappear or stop starting.

Documentation: https://hitluca.github.io/ansible-nas/
