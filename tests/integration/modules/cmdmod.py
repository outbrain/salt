import os
import integration
import tempfile
import sys

from saltunittest import skipIf

try:
    from mock import Mock, patch
    has_mock = True
except ImportError:
    has_mock = False
    patch = lambda x: lambda y: None


@skipIf(has_mock is False, "mock python module is unavailable")
class CMDModuleTest(integration.ModuleCase):
    '''
    Validate the cmd module
    '''
    def test_run(self):
        '''
        cmd.run
        '''
        shell = os.environ['SHELL']
        self.assertTrue(self.run_function('cmd.run', ['echo $SHELL']))
        self.assertEqual(
            self.run_function('cmd.run',
                              ['echo $SHELL',
                               'shell={0}'.format(shell)]).rstrip(),
            shell)

    @patch('pwd.getpwnam')
    @patch('subprocess.Popen')
    @patch('json.loads')
    def test_os_environment_remains_intact(self, *mocks):
        '''
        Make sure the OS environment is not tainted after running a command
        that specifies runas.
        '''
        environment = os.environ.copy()
        loads_mock, popen_mock, getpwnam_mock = mocks

        popen_mock.return_value = Mock(
            communicate=lambda *args, **kwags: ['{}', None],
            pid=lambda: 1,
            retcode=0
        )

        loads_mock.return_value = {'data': {'USER': 'foo'}}

        from salt.modules import cmdmod

        cmdmod.__grains__ = {'os': 'darwin'}
        if sys.platform.startswith('freebsd'):
            shell = '/bin/sh'
        else:
            shell = '/bin/bash'

        try:
            cmdmod._run('ls',
                        cwd=tempfile.gettempdir(),
                        runas='foobar',
                        shell=shell)

            environment2 = os.environ.copy()

            self.assertEquals(environment, environment2)

            getpwnam_mock.assert_called_with('foobar')
            loads_mock.assert_called_with('{}')
        finally:
            delattr(cmdmod, '__grains__')

    def test_stdout(self):
        '''
        cmd.run_stdout
        '''
        self.assertEqual(self.run_function('cmd.run_stdout',
                                           ['echo "cheese"']).rstrip(),
                         'cheese')

    def test_stderr(self):
        '''
        cmd.run_stderr
        '''
        if sys.platform.startswith('freebsd'):
            shell = '/bin/sh'
        else:
            shell = '/bin/bash'

        self.assertEqual(self.run_function('cmd.run_stderr',
                                           ['echo "cheese" 1>&2',
                                            'shell={0}'.format(shell)]
                                           ).rstrip(),
                         'cheese')

    def test_run_all(self):
        '''
        cmd.run_all
        '''
        from salt._compat import string_types

        if sys.platform.startswith('freebsd'):
            shell = '/bin/sh'
        else:
            shell = '/bin/bash'

        ret = self.run_function('cmd.run_all', ['echo "cheese" 1>&2',
                                                'shell={0}'.format(shell)])
        self.assertTrue('pid' in ret)
        self.assertTrue('retcode' in ret)
        self.assertTrue('stdout' in ret)
        self.assertTrue('stderr' in ret)
        self.assertTrue(isinstance(ret.get('pid'), int))
        self.assertTrue(isinstance(ret.get('retcode'), int))
        self.assertTrue(isinstance(ret.get('stdout'), string_types))
        self.assertTrue(isinstance(ret.get('stderr'), string_types))
        self.assertEqual(ret.get('stderr').rstrip(), 'cheese')

    def test_retcode(self):
        '''
        cmd.retcode
        '''
        self.assertEqual(self.run_function('cmd.retcode', ['true']), 0)
        self.assertEqual(self.run_function('cmd.retcode', ['false']), 1)

    def test_which(self):
        '''
        cmd.which
        '''
        self.assertEqual(self.run_function('cmd.which', ['cat']).rstrip(),
                         self.run_function('cmd.run', ['which cat']).rstrip())

    def test_has_exec(self):
        '''
        cmd.has_exec
        '''
        self.assertTrue(self.run_function('cmd.has_exec', ['python']))
        self.assertFalse(self.run_function('cmd.has_exec',
                                           ['alllfsdfnwieulrrh9123857ygf']))

    def test_exec_code(self):
        '''
        cmd.exec_code
        '''
        code = '''
import sys
sys.stdout.write('cheese')
        '''
        self.assertEqual(self.run_function('cmd.exec_code',
                                           ['python', code]).rstrip(),
                         'cheese')

    def test_quotes(self):
        '''
        cmd.run with quoted command
        '''
        cmd = '''echo 'SELECT * FROM foo WHERE bar="baz"' '''
        expected_result = 'SELECT * FROM foo WHERE bar="baz"'
        result = self.run_function('cmd.run_stdout', [cmd]).strip()
        self.assertEqual(result, expected_result)

    def test_quotes_runas(self):
        '''
        cmd.run with quoted command
        '''
        cmd = '''echo 'SELECT * FROM foo WHERE bar="baz"' '''
        expected_result = 'SELECT * FROM foo WHERE bar="baz"'

        try:
            runas = os.getlogin()
        except:
            # On some distros (notably Gentoo) os.getlogin() fails
            import pwd
            runas = pwd.getpwuid(os.getuid())[0]

        result = self.run_function('cmd.run_stdout', [cmd],
                                   runas=runas).strip()
        self.assertEqual(result, expected_result)


if __name__ == '__main__':
    from integration import run_tests
    run_tests(CMDModuleTest)
