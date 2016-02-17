from nose.tools import *
from mock import patch
from mock import call
import mock

import nose_helper

from kiwi.exceptions import (
    KiwiMountKernelFileSystemsError,
    KiwiMountSharedDirectoryError,
    KiwiSetupIntermediateConfigError
)

from kiwi.root_bind import RootBind

from kiwi.exceptions import *


class TestRootBind(object):
    def setup(self):
        root = mock.Mock()
        root.root_dir = 'root-dir'
        self.bind_root = RootBind(root)

        # stub config files and bind locations
        self.bind_root.config_files = ['/foo']
        self.bind_root.bind_locations = ['/proc']

        # stub files/dirs and mountpoints to cleanup
        self.bind_root.cleanup_files = ['/foo.kiwi']
        self.bind_root.mount_stack = ['/mountpoint']
        self.bind_root.dir_stack = ['/mountpoint']

    @raises(KiwiMountKernelFileSystemsError)
    @patch('kiwi.command.Command.run')
    @patch('kiwi.root_bind.RootBind.cleanup')
    @patch('os.path.exists')
    def test_kernel_file_systems_raises_error(
        self, mock_exists, mock_cleanup, mock_command
    ):
        mock_exists.return_value = True
        mock_command.side_effect = KiwiMountKernelFileSystemsError(
            'mount-error'
        )
        self.bind_root.mount_kernel_file_systems()
        mock.cleanup.assert_called_once_with()

    @raises(KiwiMountSharedDirectoryError)
    @patch('kiwi.command.Command.run')
    @patch('kiwi.root_bind.RootBind.cleanup')
    def test_shared_directory_raises_error(self, mock_cleanup, mock_command):
        mock_command.side_effect = KiwiMountSharedDirectoryError(
            'mount-error'
        )
        self.bind_root.mount_shared_directory()
        mock.cleanup.assert_called_once_with()

    @raises(KiwiSetupIntermediateConfigError)
    @patch('kiwi.command.Command.run')
    @patch('kiwi.root_bind.RootBind.cleanup')
    @patch('os.path.exists')
    def test_intermediate_config_raises_error(
        self, mock_exists, mock_cleanup, mock_command
    ):
        mock_exists.return_value = True
        mock_command.side_effect = KiwiSetupIntermediateConfigError(
            'config-error'
        )
        self.bind_root.setup_intermediate_config()
        mock.cleanup.assert_called_once_with()

    @patch('kiwi.command.Command.run')
    def test_mount_kernel_file_systems(self, mock_command):
        self.bind_root.mount_kernel_file_systems()
        mock_command.assert_called_once_with(
            ['mount', '-n', '--bind', '/proc', 'root-dir/proc']
        )

    @patch('kiwi.command.Command.run')
    def test_mount_shared_directory(self, mock_command):
        self.bind_root.mount_shared_directory()
        assert mock_command.call_args_list == [
            call([
                'mkdir', '-p', 'root-dir/var/cache/kiwi'
            ]),
            call([
                'mount', '-n', '--bind', '/var/cache/kiwi',
                'root-dir/var/cache/kiwi'
            ])
        ]

    @patch('kiwi.command.Command.run')
    @patch('os.path.exists')
    def test_intermediate_config(self, mock_exists, mock_command):
        mock_exists.return_value = True
        self.bind_root.setup_intermediate_config()
        assert mock_command.call_args_list == [
            call([
                'cp', '/foo', 'root-dir/foo.kiwi'
            ]),
            call([
                'ln', '-s', '-f', 'foo.kiwi', 'root-dir/foo'
            ])
        ]

    @patch('kiwi.command.Command.run')
    @patch('os.path.islink')
    def test_cleanup(self, mock_islink, mock_command):
        mock_islink.return_value = True
        self.bind_root.cleanup()

        assert mock_command.call_args_list == [
            call([
                'mountpoint', '-q', 'root-dir/mountpoint'
            ]),
            call([
                'umount', '-l', 'root-dir/mountpoint'
            ]),
            call([
                'rmdir', '-p', '--ignore-fail-on-non-empty',
                'root-dir/mountpoint'
            ]),
            call([
                'rm', '-f', 'root-dir/foo.kiwi', 'root-dir/foo'
            ])
        ]

    @patch('kiwi.command.Command.run')
    @patch('os.path.islink')
    @patch('kiwi.logger.log.warning')
    def test_cleanup_continue_on_raise(
        self, mock_warn, mock_islink, mock_command
    ):

        def side_effect(arg):
            if arg[0] == 'mountpoint':
                return
            else:
                raise Exception

        mock_command.side_effect = side_effect
        mock_islink.return_value = True
        self.bind_root.cleanup()
        assert mock_warn.called

    @patch('kiwi.command.Command.run')
    @patch('os.path.islink')
    @patch('kiwi.logger.log.warning')
    def test_cleanup_mountpoint_invalid(
        self, mock_warn, mock_islink, mock_command
    ):
        mock_islink.return_value = True
        mock_command.side_effect = Exception
        self.bind_root.cleanup()
        assert mock_command.call_args_list == [
            call([
                'mountpoint', '-q', 'root-dir/mountpoint'
            ]),
            call([
                'rmdir', '-p', '--ignore-fail-on-non-empty',
                'root-dir/mountpoint'
            ]),
            call([
                'rm', '-f', 'root-dir/foo.kiwi', 'root-dir/foo'
            ])
        ]

    def test_move_to_root(self):
        assert self.bind_root.move_to_root(
            [self.bind_root.root_dir + '/argument']
        ) == ['//argument']
