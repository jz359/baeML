import React, { Component } from 'react'
import { Switch, Route, BrowserRouter } from 'react-router-dom'
import Feed from './App';
import LoginComponent from '../containers/login_component.js';
import axios from 'axios'



class Main extends Component {

  constructor(props){
    super(props);
    this.state = {
      loggedIn: null,
      user_id: null
    }

    this.getUserID = this.getUserID.bind(this);
    this.getLoginState = this.getLoginState.bind(this);
  }

  componentDidMount() {
    window['getLoginState'] = this.getLoginState;
    window.fbAsyncInit = function(){
       window.FB.init({
        appId            : '1992517710981460',
        autoLogAppEvents : true,
        xfbml            : true,
        cookie           : true,
        status         : true,
        version          : 'v2.9'
      });
     this.getLoginState();
    };
    (function(d, s, id) {
      var js, fjs = d.getElementsByTagName(s)[0];
      if (d.getElementById(id)) return;
      js = d.createElement(s); js.id = id;
      js.src = "//connect.facebook.net/en_US/sdk.js#xfbml=1&version=v2.9&appId=1992517710981460";
      fjs.parentNode.insertBefore(js, fjs);
    }(document, 'script', 'facebook-jssdk'));
  }


  //calls FB API's getLoginStatus to determine user login status
  getLoginState() { 
    window.FB.getLoginStatus((response) => {
      if (response.status === 'connected') {
        var user_id = response.authResponse.userID
        axios.get('/api/status/', {
          params: {
            user_ID: user_id,
          }
        })
        .then((response) => { 
          //if user has been init before, log them in
          if (response.status === 200){
            console.log("hi" + user_id)
            this.setState({
                loggedIn: true,
                user_id: user_id
            });
          } else {
              this.setState({
              loggedIn: false
              });
            }
          });
      } else {
        this.setState({
            loggedIn: false
        });
      }
    });  
  }

  getUserID() {
    return this.state.user_id;
  }

  //render props will handle redirection 
  render(){
    console.log(this.state.loggedIn)
    return ( this.state.loggedIn !== null ?
        (<Switch>  
          <Route exact path='/' render={()=> (
              this.state.loggedIn ? <Feed userID={this.state.user_id} loginStatus={this.getLoginState}/> : <LoginComponent fb={window.FB} loginStatus={this.getLoginState}/>
            )
          }/>
          <Route render={
            function() {
              return (<p> Not Found </p>)
            }
          }/>
        </Switch>) : null);
  }
}

const Root = () => (
  // <Provider store={store}>
    <BrowserRouter>
      <Main />
    </BrowserRouter>
  // </Provider>
)




// Root.propTypes = {
//   store: PropTypes.object.isRequired
// }

export default Root