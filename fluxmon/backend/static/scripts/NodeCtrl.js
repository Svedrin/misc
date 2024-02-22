fluxmon.controller("NodeCtrl", function($scope, $stateParams, $http, $rootScope){
    $http.get("/api/hosts/" + $stateParams.nodeId + "/").then(function(response){
        $scope.host = response.data;
        $rootScope.titlePrefix = $scope.host.fqdn.split('.')[0];
    });
});

fluxmon.controller("NodeCheckListCtrl", function($scope, $stateParams, $http){
    $http.get("/api/checks/", {params: {
      target_host: $stateParams.nodeId
    }}).then(function(response){
        $scope.hostChecks = response.data.results;
    });
});

fluxmon.controller("NodeCheckCtrl", function($scope, $state, $stateParams, $http, $timeout, $rootScope, isMobile){
    $scope.showDetails = !isMobile.any() || $state.is("node.check.varlist");
    $rootScope.$on('$stateChangeSuccess', function(ev, toState, toParams, frState, frParams){
        $scope.showDetails = !isMobile.any() || toState.name == "node.check.varlist";
    });
    $http.get("/api/checks/" + $stateParams.check + "/").then(function(response){
        $scope.check = response.data;
        $scope.editing = false;
        $scope.startEdit = function(){
          $scope.editing = true;
          $timeout(function(){
            var inp = $('#id_display');
            inp.focus();
            inp.get(0).setSelectionRange($scope.check.display.length, $scope.check.display.length)
          }, 50);
        };
        $scope.submit = function(){
          $http.patch("/api/checks/" + $stateParams.check + "/", {
            display: $scope.check.display
          });
          $scope.editing = false;
        };
//         $(document).keypress(function(ev){
//             if(ev.key == 'e'){
//                 ev.preventDefault();
//                 $timeout($scope.startEdit, 10);
//             }
//         });
    });
});

fluxmon.controller("NodeCheckVarCtrl", function($scope, $stateParams, $http){
    $scope.domain = null;
    $scope.$watch("check", function(){
        if(!$scope.check) return;
        $scope.variables = $scope.check.sensor.sensorvariable_set.filter(function(item){
            if(item.name == $stateParams.name){
                return true;
            }
        });
    });
    $scope.graphState = {};
});

fluxmon.controller("NodeCheckViewCtrl", function($scope, $stateParams, $http){
    $scope.domain = null;
    $scope.$watch("check", function(){
        if(!$scope.check) return;
        $scope.variables = $scope.check.views_set.reduce(function(prev, item){
            if(item.name == $stateParams.name){
                return item.variables;
            }
            return prev;
        }, []);
    });
    $scope.graphState = {};
});
