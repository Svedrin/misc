fluxmon.controller("TokenCtrl", function($scope, $stateParams, $http){
    $scope.domain = null;
    $scope.check  = null;
    $scope.token  = $stateParams.token;
    $scope.graphState = {};
    $http.get("/api/tokens/" + $stateParams.token + "/", {
        headers: {
            "Authorization": "Token " + $stateParams.token
        }
    }).then(function(response){
        $scope.check = response.data.check;
        $scope.domain = response.data.domain;
        if(response.data.view != null){
            $scope.variables = response.data.view.variables;
        }
        else{
            $scope.variables = [response.data.variable];
        }
    });
});

fluxmon.service("TokenService", function($http){
    return {
        create: function(check, domain, variable, view){
            params = {};
            if( check    ) params.check    = check.uuid;
            if( domain   ) params.domain   = domain.id;
            if( variable ) params.variable = variable.sensor + '.' + variable.name;
            if( view     ) params.view     = view;
            return $http.post('/api/tokens/', params);
        }
    }
});
