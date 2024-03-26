import npyscreen
import pendulum
from greenflow.storage import ExpStorage
from pprint import pformat
import yaml


class ExperimentList(npyscreen.MultiLineAction):
    def __init__(self, *args, **keywords):
        super(ExperimentList, self).__init__(*args, **keywords)

        self.scroll_exit = False
        self.always_show_cursor = True

    def actionHighlighted(self, act_on_this, keypress):
        self.parent.updateExperiment()

    def display_value(self, vl):
        experiment = self.parent.parentApp.getExperiment(vl)
        return f"{vl} - {pendulum.parse(experiment['stopped_ts']).diff_for_humans()} {experiment['exp_name']}"


class ExperimentForm(npyscreen.ActionFormWithMenus):
    def create(self):
        self.experiment_list = self.add(
            ExperimentList, name="Experiment ID", max_height=8
        )

        # self.experiment_list = self.add(
        #     ExperimentList,
        #     name="Experiment ID",
        #     values=[self.render_exp_in_list(exp) for exp in sorted(self.parentApp.yamldata.keys(), key=self.parentApp.sort_by_time, reverse=True)],
        #     max_height=8,
        #     )
        self.name = self.add(npyscreen.TitleText, name="Experiment name")
        self.stop = self.add(npyscreen.TitleText, name="Experiment stop time")
        self.parameters = self.add(npyscreen.TitlePager, name="Parameters")

        self.name.value = "N/A"
        self.stop.value = "N/A"
        self.parameters.value = "N/A"

        # Update experiment if possible
        if self.experiment_list.values:
            self.updateExperiment()

        exp_ids = sorted(
            self.parentApp.yamldata.keys(),
            key=self.parentApp.sort_by_time,
            reverse=True,
        )
        self.experiment_list.values = exp_ids

        # for exp_id in exp_ids:
        #     experiment = self.parentApp.getExperiment(exp_id)
        #     self.experiment_list.values.append(self.render_exp_in_list(exp_id))

        # self.experiment_list.slow_refresh = False
        # self.experiment_list.entry_widget.update()

        # Update experiment if possible
        if self.experiment_list.values:
            self.updateExperiment()

    def render_exp_in_list(self, exp_id):
        exp = self.parentApp.yamldata[exp_id]
        return f"{exp_id} - {exp['exp_name']}"

    def updateExperiment(self):
        key = self.experiment_list.values[self.experiment_list.cursor_line]
        experiment = self.parentApp.getExperiment(key)
        self.name.value = experiment["exp_name"]
        self.stop.value = experiment["stopped_ts"]
        # self.parameters.value = pformat(experiment['experiment_metadata']['factors'])
        results = experiment["experiment_metadata"].get("results", None)
        full_data = dict(
            factors=experiment["experiment_metadata"]["factors"],
            # results=experiment["experiment_metadata"]["factors"],
            # dashboard_url=experiment["experiment_metadata"]["dashboard_url"],
            # explore_url=experiment["experiment_metadata"]["explore_url"],
        )
        if results:
            full_data["results"] = results

        # self.parameters.values = yaml.dump(experiment['experiment_metadata']['factors']).split('\n')
        self.parameters.values = yaml.safe_dump(full_data).split("\n")

        # self.parameters.values = pformat(experiment['experiment_metadata']['factors']).split('\n')
        self.display()


class ExperimentApp(npyscreen.NPSAppManaged):
    def onStart(self):
        self.storage = ExpStorage()
        self.yamldata = {exp.doc_id: exp for exp in self.storage.experiments.all()}
        self.addForm("MAIN", ExperimentForm)

    def getExperiment(self, name):
        return self.yamldata[name]

    def sort_by_time(self, exp_id):
        date_time_str = self.yamldata[exp_id]["started_ts"]
        return pendulum.parse(date_time_str)

    def onCleanExit(self):
        npyscreen.notify_wait("Goodbye!")


if __name__ == "__main__":
    app = ExperimentApp()
    app.run()
