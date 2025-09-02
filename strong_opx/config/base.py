import configparser
import os


class Config(configparser.ConfigParser):
    def __init__(self, config_path: str):
        self.config_path = config_path
        super().__init__()

        self.read([self.config_path])

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            self.write(f)


class SystemConfig(Config):
    def set(self, section: str, *args, **kwargs) -> None:
        if section not in self:
            self.add_section(section)

        super().set(section, *args, **kwargs)

    def register_project(self, name: str, path: str):
        if "projects" not in self:
            self.add_section("projects")

        self.set("projects", name, path)
        self.save()

    def unregister_project(self, name: str):
        if "projects" not in self:
            self.add_section("projects")

        self.remove_option("projects", name)
        self.save()

    @property
    def registered_projects(self) -> list[str]:
        projects = []

        if "projects" not in self:
            return projects

        return list(self["projects"].keys())

    def get_project_path(self, name: str) -> str:
        return self.get("projects", name)

    def get_project_config_dir(self, project_name: str) -> str:
        return os.path.join(os.path.dirname(self.config_path), project_name)

    def get_project_config(self, project_name: str) -> Config:
        project_config_path = os.path.join(self.get_project_config_dir(project_name), "config")
        return Config(project_config_path)
