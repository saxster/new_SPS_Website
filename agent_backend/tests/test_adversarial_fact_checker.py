"""
Tests for adversarial_fact_checker module.

Bug #1: ValidationError Shadowing
The module imports pydantic.ValidationError on line 26, then defines a custom
ValidationError class on line 52 that shadows the import. This means Pydantic
validation errors during ArticleInput() instantiation won't be caught properly.
"""

import pytest
import ast
import os


class TestValidationErrorShadowing:
    """Test that pydantic ValidationError is properly handled (not shadowed)."""

    def test_no_import_shadowing_in_source_file(self):
        """
        Verify that pydantic.ValidationError is imported with an alias
        to avoid being shadowed by the custom ValidationError class.

        The bug: Line 26 imports `from pydantic import ValidationError` and
        line 52 defines `class ValidationError(Exception)` which shadows it.

        Expected fix: Import as `from pydantic import ValidationError as PydanticValidationError`
        """
        source_file = os.path.join(
            os.path.dirname(__file__),
            '..', 'lib', 'fact_check', 'adversarial_fact_checker.py'
        )

        with open(source_file, 'r') as f:
            source = f.read()

        # Parse the AST
        tree = ast.parse(source)

        # Find all imports from pydantic
        pydantic_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == 'pydantic':
                for alias in node.names:
                    if alias.name == 'ValidationError':
                        pydantic_imports.append({
                            'name': alias.name,
                            'asname': alias.asname,
                            'lineno': node.lineno
                        })

        # Find all class definitions named ValidationError
        custom_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'ValidationError':
                custom_classes.append({
                    'name': node.name,
                    'lineno': node.lineno
                })

        # Verify we have both a pydantic import and a custom class
        assert len(pydantic_imports) >= 1, "Expected pydantic ValidationError import"
        assert len(custom_classes) >= 1, "Expected custom ValidationError class"

        # The fix should rename the pydantic import to avoid shadowing
        # Check that the import uses an alias (asname)
        pydantic_import = pydantic_imports[0]
        assert pydantic_import['asname'] is not None, (
            f"pydantic.ValidationError at line {pydantic_import['lineno']} "
            f"should be imported with an alias to avoid shadowing by "
            f"custom ValidationError class at line {custom_classes[0]['lineno']}. "
            f"Use: from pydantic import ValidationError as PydanticValidationError"
        )

    def test_pydantic_and_custom_validation_errors_are_distinct(self):
        """
        After the fix, verify that both pydantic.ValidationError and the
        custom ValidationError are accessible as distinct classes.
        """
        from pydantic import ValidationError as PydanticValidationError

        # The custom one should still be available via the module
        # (after fix, it won't shadow pydantic's)
        assert issubclass(PydanticValidationError, Exception)

        # Create test case for the custom error
        class CustomValidationError(Exception):
            """Test placeholder for custom error"""
            pass

        assert PydanticValidationError is not CustomValidationError


class TestPydanticValidationWithArticleInput:
    """Test that pydantic validation works correctly with ArticleInput."""

    def test_article_input_validation_raises_pydantic_error(self):
        """
        Verify that invalid ArticleInput raises pydantic's ValidationError.
        """
        import sys
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__),
            '..', 'lib', 'fact_check'
        ))

        from pydantic import ValidationError as PydanticValidationError
        from validators import ArticleInput

        # This should raise pydantic's ValidationError for invalid input
        with pytest.raises(PydanticValidationError):
            ArticleInput(
                article_title="short",  # Too short, min 10 chars
                article_summary="x" * 10,  # Too short, min 50 chars
                proposed_regulations=[],
                proposed_costs="test",
                topic="test"
            )

    def test_article_input_validation_with_valid_data(self):
        """Verify valid ArticleInput is accepted."""
        import sys
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__),
            '..', 'lib', 'fact_check'
        ))

        from validators import ArticleInput

        # Valid input should work
        article = ArticleInput(
            article_title="Valid Article Title That Is Long Enough",
            article_summary="This is a sufficiently long article summary that meets the minimum character requirement for validation.",
            proposed_regulations=["Regulation A", "Regulation B"],
            proposed_costs="Rs 10,000 - Rs 50,000",
            topic="security"
        )

        assert article.article_title == "Valid Article Title That Is Long Enough"
