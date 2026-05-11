from boxes.util import human_size, detect_host_arch


class TestHumanSize:
    def test_bytes(self) -> None:
        assert human_size(0) == "0.0 B"
        assert human_size(512) == "512.0 B"
        assert human_size(1023) == "1023.0 B"

    def test_kilobytes(self) -> None:
        assert human_size(1024) == "1.0 KB"
        assert human_size(2048) == "2.0 KB"
        assert human_size(1536) == "1.5 KB"

    def test_megabytes(self) -> None:
        result = human_size(1048576)
        assert "MB" in result

    def test_gigabytes(self) -> None:
        result = human_size(1073741824)
        assert "GB" in result

    def test_terabytes(self) -> None:
        result = human_size(1099511627776)
        assert "TB" in result


class TestDetectHostArch:
    def test_returns_string(self) -> None:
        arch = detect_host_arch()
        assert isinstance(arch, str)
        assert arch in ("x86_64", "aarch64", "i386")
