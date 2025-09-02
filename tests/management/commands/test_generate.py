from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from unittest.mock import Mock, create_autospec, patch

import pytest

from strong_opx.exceptions import CommandError
from strong_opx.management.command import ProjectCommand
from strong_opx.management.commands.generate import Command
from strong_opx.project import Project


class TestAddArguments:
    @dataclass
    class Fixture:
        argument_parser: ArgumentParser
        parsed_args: Namespace
        subject: Command
        super_add_arguments_mock: Mock

    @pytest.fixture
    @patch.object(ProjectCommand, "add_arguments", autospec=True)
    def setup(self, super_add_arguments_mock: Mock):
        argument_parser = ArgumentParser()
        subject = Command()
        subject.add_arguments(argument_parser)

        parsed_args: Namespace = argument_parser.parse_args(["what_value"])

        return self.Fixture(
            argument_parser=argument_parser,
            parsed_args=parsed_args,
            subject=subject,
            super_add_arguments_mock=super_add_arguments_mock,
        )

    def test_calls_super_add_arguments(self, setup: Fixture):
        setup.super_add_arguments_mock.assert_called_once_with(setup.subject, setup.argument_parser)

    def test_parses_what_argument(self, setup: Fixture):
        assert setup.parsed_args.what == "what_value"


class TestHandle:
    class TestSuccess:
        @dataclass
        class Fixture:
            import_module_mock: Mock
            generator_constructor_mock: Mock
            generator_instance: Mock
            project_instance: Mock

        @pytest.fixture
        @patch("strong_opx.management.commands.generate.importlib.import_module", autospec=True)
        def setup(self, import_module_mock: Mock):
            generator_constructor_mock = Mock()
            generator_instance = generator_constructor_mock.return_value

            import_module_mock.return_value = Mock(Generator=generator_constructor_mock)
            project_instance = create_autospec(spec=Project, instance=True)

            subject = Command()
            subject.handle(project_instance, "what_value")

            return self.Fixture(
                import_module_mock=import_module_mock,
                generator_constructor_mock=generator_constructor_mock,
                generator_instance=generator_instance,
                project_instance=project_instance,
            )

        def test_imports_generator_module(self, setup: Fixture):
            setup.import_module_mock.assert_called_once_with("strong_opx.codegen.generators.what_value")

        def test_calls_generator_constructor(self, setup: Fixture):
            setup.generator_constructor_mock.assert_called_once_with(setup.project_instance)

        def test_calls_generate_on_generator_instance(self, setup: Fixture):
            setup.generator_instance.generate.assert_called_once_with()

    class TestFailureNoGeneratorClass:
        """
        Tests when the requested module exists, but does not contain a Generator class.
        """

        @dataclass
        class Fixture:
            import_module_mock: Mock

        @pytest.fixture
        @patch("strong_opx.management.commands.generate.importlib.import_module", autospec=True)
        def setup(self, import_module_mock: Mock):
            imported_module = import_module_mock.return_value
            del imported_module.Generator

            project_instance = create_autospec(spec=Project, instance=True)

            subject = Command()
            with pytest.raises(AttributeError):
                subject.handle(project_instance, "what_value")

            return self.Fixture(import_module_mock=import_module_mock)

        def test_imports_generator_module(self, setup: Fixture):
            setup.import_module_mock.assert_called_once_with("strong_opx.codegen.generators.what_value")

    class TestFailureModuleNotFound:
        """
        Tests when the requested module does not exist.
        """

        @dataclass
        class Fixture:
            exception_info: any
            import_module_mock: Mock

        @pytest.fixture
        @patch("strong_opx.management.commands.generate.importlib.import_module", autospec=True)
        def setup(self, import_module_mock: Mock):
            import_module_mock.side_effect = ModuleNotFoundError

            project_instance = create_autospec(spec=Project, instance=True)

            subject = Command()
            with pytest.raises(CommandError) as exception_info:
                subject.handle(project_instance, "what_value")

            return self.Fixture(exception_info=exception_info, import_module_mock=import_module_mock)

        def test_imports_generator_module(self, setup: Fixture):
            setup.import_module_mock.assert_called_once_with("strong_opx.codegen.generators.what_value")

        def test_raises_command_error(self, setup: Fixture):
            expected_message = "Unknown generator: what_value"
            assert str(setup.exception_info.value) == expected_message
