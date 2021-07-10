import pytest

from utils.cmdparse.cmdspec import ArgSpec

class TestArgSpec:
    @pytest.mark.parametrize('args', [
        ("noasd sadjkbj3ASDKLj3kNasd aks dkabsjd", "Asdihoasd£Ljaposdj9037152078!\"(£^!\"^*)", int),
        ("", "Asdihoasd£Ljaposdj9037152078!\"(£^!\"^*)", str),
        ("noasd sadjkbj3Aabsjd", ""),
        ("noasd s aks dkabsjd", "Asdihoas(£^!\"^*)")])
    def test_by_position(self, args):
        arg_spec = ArgSpec(*args)
        assert arg_spec[0] == args[0]
        assert arg_spec.name == args[0]
        assert arg_spec[1] == args[1]
        assert arg_spec.description == args[1]
        if len(args) >= 3:
            assert arg_spec[2] == args[2]
            assert arg_spec.conversion == args[2]
        else:
            assert arg_spec[2] == arg_spec.conversion

    @pytest.mark.parametrize('args', [
        ("noasd sadjkbj3ASDKLj3kNasd aks dkabsjd", "Asdihoasd£Ljaposdj9037152078!\"(£^!\"^*)", int),
        ("", "Asdihoasd£Ljaposdj9037152078!\"(£^!\"^*)", str),
        ("noasd sadjkbj3Aabsjd", ""),
        ("noasd s aks dkabsjd", "Asdihoas(£^!\"^*)")])
    def test_by_name(self, args):
        arg_spec = ArgSpec(**{k:v for k,v in zip(["name","description","conversion"], args)})
        assert arg_spec[0] == args[0]
        assert arg_spec.name == args[0]
        assert arg_spec[1] == args[1]
        assert arg_spec.description == args[1]
        if len(args) >= 3:
            assert arg_spec[2] == args[2]
            assert arg_spec.conversion == args[2]
        else:
            assert arg_spec[2] == arg_spec.conversion

    @pytest.mark.parametrize('arg', [
        "asdasd",
        "Asdihoasd£Ljaposdj9037152078!\"(£^!\"^*)",
        "noasd sadjkbj3Aabsjd", "",
        "noasd s aks dkabsjd", "Asdihoas(£^!\"^*)"])
    def test_default_conversion_is_identity(self,arg):
        arg_spec = ArgSpec("","")
        assert arg_spec.conversion(arg) == arg
