from rest_framework.response import Response
from rest_framework.views import APIView

from .evaluation import evaluate


class EvaluationView(APIView):
    """GET /api/evaluation/?threshold=0.5&repo=owner/name&holdout=1"""

    def get(self, request):
        try:
            threshold = float(request.query_params.get("threshold", 0.5))
        except ValueError:
            return Response({"detail": "threshold must be a number"}, status=400)
        holdout = request.query_params.get("holdout", "1") != "0"
        return Response(evaluate(threshold, request.query_params.get("repo"), holdout))
