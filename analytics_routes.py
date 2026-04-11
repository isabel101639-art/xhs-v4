from flask import jsonify, render_template, request

from models import Activity


def register_analytics_routes(app, helpers):
    build_dashboard_stats = helpers['build_dashboard_stats']
    build_report_markdown = helpers['build_report_markdown']

    @app.route('/data_analysis')
    def data_analysis():
        activities = Activity.query.order_by(Activity.created_at.desc()).all()
        return render_template('data_analysis.html', activities=activities)

    @app.route('/api/stats/<int:activity_id>')
    def get_stats(activity_id):
        return jsonify(build_dashboard_stats(activity_id, request.args))

    @app.route('/api/weekly_report/<int:activity_id>')
    def export_weekly_report(activity_id):
        activity = Activity.query.get_or_404(activity_id)
        stats = build_dashboard_stats(activity_id, request.args)
        report = build_report_markdown(activity, stats, report_type='weekly')
        return report, 200, {
            'Content-Type': 'text/markdown; charset=utf-8',
            'Content-Disposition': f"attachment; filename=weekly_report_activity_{activity_id}.md"
        }

    @app.route('/api/monthly_report/<int:activity_id>')
    def export_monthly_report(activity_id):
        activity = Activity.query.get_or_404(activity_id)
        stats = build_dashboard_stats(activity_id, request.args)
        report = build_report_markdown(activity, stats, report_type='monthly')
        return report, 200, {
            'Content-Type': 'text/markdown; charset=utf-8',
            'Content-Disposition': f"attachment; filename=monthly_report_activity_{activity_id}.md"
        }

    @app.route('/api/review_report/<int:activity_id>')
    def export_review_report(activity_id):
        activity = Activity.query.get_or_404(activity_id)
        stats = build_dashboard_stats(activity_id, request.args)
        report = build_report_markdown(activity, stats, report_type='review')
        return report, 200, {
            'Content-Type': 'text/markdown; charset=utf-8',
            'Content-Disposition': f"attachment; filename=review_report_activity_{activity_id}.md"
        }
