fluxmon.controller("SearchCtrl", function($scope, $state, $stateParams, $http, $location){
    $scope.submit = function(initial){
        if( !initial ){
            $state.go("search", {query: $scope.query});
            return;
        }
        $http.get("/api/checks/", {params: {
            search: $scope.query
        }}).then(function(response){
            $scope.foundChecks = response.data.results;
        });
    };

    if($stateParams.query){
        $scope.query = $stateParams.query;
        $scope.submit(true);
    }
});

fluxmon.directive('searchbox', function($compile){
    return {
        restrict: 'A',
        scope: {},
        controller: function($scope, $state){
            $scope.submit = function(){
                $state.go("search", {query: $scope.query});
            };
        },
        link: function($scope, element, attr){
            $(element).popover({
              trigger: "manual",
              title: "Search",
              content: $compile('<input type="text" class="form-control" ng-model="query" ng-enter="submit()" placeholder="Query" style="width: 250px" />')($scope),
              placement: "bottom",
              html: true
            });
            $(element).on("shown.bs.popover", function(){
              var inp = $(element).siblings().find('input');
              inp.focus();
              inp.blur(function(){
                $(element).popover('hide');
              });
            });
            $(element).click(function(ev){
              ev.preventDefault();
              $(this).popover('toggle');
            });
            $(document).keypress(function(ev){
                if(ev.key == '.'){
                    ev.preventDefault();
                    $(element).popover('toggle');
                }
            });
        }
    };
});
