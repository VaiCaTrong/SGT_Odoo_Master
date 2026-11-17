'use strict';
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const assert = require('assert');
const source=fs.readFileSync(path.resolve(__dirname, '../static/src/js/geo_coordinate_actions.js'),'utf8')
 .replace(/^import .*;\r?\n/gm,'').replace('export class Crm005GeoActions','class Crm005GeoActions');
let componentRegistration = null;
const notices=[];
const context={
    Component:class {}, standardFieldProps:{},
    registry:{category:(name)=>{assert.equal(name,'fields');return {add:(key,value)=>componentRegistration={key,value}};}},
    useService:()=>({add:(s,p)=>notices.push({s,p})}),
    navigator:{clipboard:{writeText:async(value)=>{context.copied=value;}}},
    document:{},
    encodeURIComponent,
    Number,
};
vm.runInNewContext(source+'\nthis.Crm005GeoActions=Crm005GeoActions;',context);
assert.equal(componentRegistration.key,'sgt_crm005_geo_actions');
const action=new context.Crm005GeoActions();
action.props={record:{data:{x_yp_latitude:20.8497977,x_yp_longitude:106.6621584}}};
action.setup();
assert.equal(action.coordinates,'20.8497977, 106.6621584');
assert.equal(action.mapUrl,'https://www.google.com/maps/search/?api=1&query=20.8497977%2C%20106.6621584');
const fakeEvent={preventDefault(){},stopPropagation(){}};
(async()=>{
 await action.copyCoordinates(fakeEvent);
 assert.equal(context.copied,'20.8497977, 106.6621584');
 assert.equal(notices.length,1);
 action.props.record.data={x_yp_latitude:0,x_yp_longitude:0};
 assert.equal(action.coordinates,null);
 assert.equal(action.mapUrl,'');
 action.props.record.data={x_yp_latitude:91,x_yp_longitude:106};
 assert.equal(action.coordinates,null);
 action.props.record.data={x_yp_latitude:0,x_yp_longitude:106};
 assert.equal(action.coordinates,'0, 106');
 action.props.record.data={x_yp_latitude:-10.9,x_yp_longitude:106.65};
 assert.equal(action.coordinates,'-10.9, 106.65');
 console.log('6 JS coordinate scenarios passed');
})().catch((e)=>{console.error(e);process.exit(1);});
