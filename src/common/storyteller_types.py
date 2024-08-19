from typing import Optional, Any, Dict


from common.storyteller_exceptions import StorytellerMissingAttributeError


class StorytellerContentPacket:
    """
    A class to encapsulate content and metadata for serialization and deserialization.

    This class is used to package serialized content along with its metadata, such as file name,
    file extension, and the plugin used for serialization/deserialization.

    Attributes:
        content (str): The serialized content.
        file_name (str): The name of the file.
        file_extension (Optional[str]): The file extension (optional).
        plugin_name (Optional[str]): The name of the plugin used for serialization/deserialization (optional).
        stage_name (Optional[str]): The name of the stage (optional).
        phase_name (Optional[str]): The name of the phase (optional).
        metadata (Dict[str, Any]): Additional metadata related to the content.
    """

    def __init__(
        self,
        content: str,
        file_name: str,
        file_extension: Optional[str] = None,
        plugin_name: Optional[str] = None,
        stage_name: Optional[str] = None,
        phase_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.content = content
        self.file_name = file_name
        self._file_extension = file_extension
        self._plugin_name = plugin_name
        self._stage_name = stage_name
        self._phase_name = phase_name
        self.metadata = metadata if metadata is not None else {}

    @property
    def file_extension(self) -> str:
        if self._file_extension is None:
            raise StorytellerMissingAttributeError("file_extension")
        return self._file_extension

    @property
    def plugin_name(self) -> str:
        if self._plugin_name is None:
            raise StorytellerMissingAttributeError("plugin_name")
        return self._plugin_name

    @property
    def stage_name(self) -> str:
        if self._stage_name is None:
            raise StorytellerMissingAttributeError("stage_name")
        return self._stage_name

    @property
    def phase_name(self) -> str:
        if self._phase_name is None:
            raise StorytellerMissingAttributeError("phase_name")
        return self._phase_name

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the ContentPacket to a dictionary.

        Returns:
            Dict[str, Any]: The content packet as a dictionary.
        """
        return {
            "content": self.content,
            "file_name": self.file_name,
            "file_extension": self._file_extension,
            "plugin_name": self._plugin_name,
            "stage_name": self._stage_name,
            "phase_name": self._phase_name,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StorytellerContentPacket":
        """
        Create a ContentPacket instance from a dictionary.

        Args:
            data (Dict[str, Any]): A dictionary containing the packet's data.

        Returns:
            ContentPacket: A new ContentPacket instance.
        """
        return cls(
            content=data.get("content", ""),
            file_name=data.get("file_name", ""),
            file_extension=data.get("file_extension"),
            plugin_name=data.get("plugin_name"),
            stage_name=data.get("stage_name"),
            phase_name=data.get("phase_name"),
            metadata=data.get("metadata", {}),
        )
